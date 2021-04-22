import json
import logging
import signal
import sys
import time
import traceback
from datetime import datetime, timedelta
from threading import Lock, Thread

import pytz
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from requests_oauthlib import OAuth1Session

from oh_template.settings import NUM_OF_SUMMARY_UPLOAD_THREADS
from .consts import BACKFILL_SECONDS, BACKFILL_MIN_YEAR, GARMIN_BACKFILL_URLS, BACKFILL_SLEEP_BETWEEN_CALLS
from .helpers import unix_time_seconds, merge_with_existing_and_upload, get_oh_user_from_garmin_id, group_summaries_per_user_and_per_month, extract_summaries, remove_fields, summaries_to_process_key, \
    remove_unwanted_fields, extract_timestamp
from .models import GarminMember, SummariesToProcess, RetrievedData

utc = pytz.UTC

_LOGGER = logging.getLogger(__name__)

handle_summaries_lock = Lock()
locked_summaries = []
process_terminated = False


def terminate_process(signum, frame):
    global process_terminated
    process_terminated = True


def start_threads():
    signal.signal(signal.SIGINT, terminate_process)
    signal.signal(signal.SIGTERM, terminate_process)

    backfill_thread = Thread(target=handle_backfill)
    backfill_thread.start()

    for i in range(NUM_OF_SUMMARY_UPLOAD_THREADS):
        thread = Thread(target=handle_summaries)
        thread.start()


def handle_backfill():
    while not process_terminated:
        try:
            garmin_member = GarminMember.objects.get(was_backfilled=False, userid__isnull=False)
            handle_backfill_for_member(garmin_member)
        except ObjectDoesNotExist:
            # Nothing to do
            time.sleep(0.5)


def handle_backfill_for_member(garmin_member):
    oauth = OAuth1Session(
        client_key=settings.GARMIN_KEY,
        client_secret=settings.GARMIN_SECRET,
        resource_owner_key=garmin_member.access_token,
        resource_owner_secret=garmin_member.access_token_secret
    )
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(seconds=BACKFILL_SECONDS)
    _LOGGER.info(f"Executing backfill for user ${get_oh_user_from_garmin_id(garmin_member.userid)}")
    while start_date.year >= BACKFILL_MIN_YEAR:

        start_epoch = unix_time_seconds(start_date)
        end_epoch = unix_time_seconds(end_date)

        for url in GARMIN_BACKFILL_URLS:
            summary_url = f"{url}?summaryStartTimeInSeconds={start_epoch}&summaryEndTimeInSeconds={end_epoch}"
            res = oauth.get(url=summary_url)
            if res.status_code != 202:
                _LOGGER.error(f"Invalid response for backfill url {summary_url}, got response response: {res.content},{res.status_code}")
                # Failed to call all backfill's !!
                # We'll stop executing them for this user, in the next run of the handle_backfill thread,
                # this function will be called again for this user, since garmin_member.was_backfilled is still False
                return
            else:
                _LOGGER.info(f"Called backfill {summary_url}")

            time.sleep(BACKFILL_SLEEP_BETWEEN_CALLS)

        end_date = start_date
        start_date = start_date - timedelta(seconds=BACKFILL_SECONDS)
    garmin_member.was_backfilled = True
    garmin_member.save()


def handle_summaries():
    while not process_terminated:
        not_locked_summaries = None
        with handle_summaries_lock:
            for summaries_to_process in SummariesToProcess.objects.all():
                if summaries_to_process_key(summaries_to_process) not in locked_summaries:
                    not_locked_summaries = summaries_to_process
                    break

            if not_locked_summaries is not None:
                key = summaries_to_process_key(not_locked_summaries)
                locked_summaries.append(key)

        if not_locked_summaries is not None:
            try:
                process_summaries_for_user_and_file(not_locked_summaries.file_name, not_locked_summaries.garmin_user_id)
            finally:
                locked_summaries.remove(summaries_to_process_key(not_locked_summaries))

        else:
            # Nothing to do
            time.sleep(0.5)


def update_retrieved_data_log(oh_user, summaries, file_name):
    if len(summaries) == 0:
        return  # Nothing to do
    data_type = "-".join(file_name.split("-")[:-2])
    min_timestamp = min(map(lambda summary: extract_timestamp(summary).timestamp(), summaries))
    max_timestamp = max(map(lambda summary: extract_timestamp(summary).timestamp(), summaries))
    min_date = utc.localize(datetime.fromtimestamp(min_timestamp))
    max_date = utc.localize(datetime.fromtimestamp(max_timestamp))
    with handle_summaries_lock:
        try:
            retrieved_data = RetrievedData.objects.get(member=oh_user, data_type=data_type)
            retrieved_data.min_date = min_date if min_date < retrieved_data.min_date else retrieved_data.min_date
            retrieved_data.max_date = max_date if max_date > retrieved_data.max_date else retrieved_data.max_date
        except ObjectDoesNotExist:
            retrieved_data = RetrievedData(member=oh_user, data_type=data_type, min_date=min_date, max_date=max_date)
        retrieved_data.save()


def process_summaries_for_user_and_file(file_name, garmin_user_id):
    summaries_to_process_all = SummariesToProcess.objects.filter(garmin_user_id__exact=garmin_user_id, file_name__exact=file_name)
    summaries = []
    ids_to_delete = []
    for summaries_to_process in summaries_to_process_all:
        ids_to_delete.append(summaries_to_process.id)
        summaries += json.loads(summaries_to_process.summaries_json)

    try:
        oh_user = get_oh_user_from_garmin_id(garmin_user_id)
        all_summaries = merge_with_existing_and_upload(oh_user, summaries, file_name)
        update_retrieved_data_log(oh_user, all_summaries, file_name)
        SummariesToProcess.objects.filter(id__in=ids_to_delete).delete()
        _LOGGER.info(f"Saved {len(all_summaries)} summaries for garmin_user_id={garmin_user_id}, file_name={file_name}")

    except:
        e = sys.exc_info()[0]
        _LOGGER.error(f"Failed to handle summaries JSON {file_name} {e}")
        traceback.print_exc()

        # Reschedule handling
        save_summaries_for_delayed_processing(file_name, garmin_user_id, summaries)


def handle_summaries_delayed(body, summaries_name, data_type, fields_to_remove=None):
    body = body.decode('utf-8')
    summaries = extract_summaries(body, summaries_name)
    if fields_to_remove is not None:
        remove_fields(summaries, fields_to_remove)
    grouped_summaries = group_summaries_per_user_and_per_month(summaries)
    for garmin_user_id, monthly_summaries in grouped_summaries.items():
        for year_month, summaries in monthly_summaries.items():
            file_name = f"{data_type}-{year_month}"
            remove_unwanted_fields(summaries)
            save_summaries_for_delayed_processing(file_name, garmin_user_id, summaries)


def save_summaries_for_delayed_processing(file_name, garmin_user_id, summaries):
    _LOGGER.info(f"Saving {len(summaries)} summaries {file_name} for user {garmin_user_id} for further processing")
    summaries_to_process = SummariesToProcess()
    summaries_to_process.summaries_json = json.dumps(summaries)
    summaries_to_process.garmin_user_id = garmin_user_id
    summaries_to_process.file_name = file_name
    summaries_to_process.save()
