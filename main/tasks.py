import json
import logging
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone

from celery.decorators import task
from django.conf import settings
from django.utils.timezone import make_aware
from ohapi import api
from requests_oauthlib import OAuth1Session

from .consts import BACKFILL_SECONDS, BACKFILL_MIN_YEAR, GARMIN_BACKFILL_URLS, BACKFILL_SLEEP_BETWEEN_CALLS
from .helpers import unix_time_seconds, upload_summaries_for_month, group_summaries_per_user_and_per_month, get_oh_user_from_garmin_id, remove_unwanted_fields
from .models import GarminMember

_LOGGER = logging.getLogger(__name__)


@task
def handle_backfill(garmin_user_id):
    garmin_member = GarminMember.objects.get(userid=garmin_user_id)
    oauth = OAuth1Session(
        client_key=settings.GARMIN_KEY,
        client_secret=settings.GARMIN_SECRET,
        resource_owner_key=garmin_member.access_token,
        resource_owner_secret=garmin_member.access_token_secret
    )

    end_date = datetime.utcnow()
    start_date = end_date - timedelta(seconds=BACKFILL_SECONDS)

    _LOGGER.info(f"Executing backfill for user ${get_oh_user_from_garmin_id(garmin_user_id)}")
    while start_date.year >= BACKFILL_MIN_YEAR:

        start_epoch = unix_time_seconds(start_date)
        end_epoch = unix_time_seconds(end_date)

        for url in GARMIN_BACKFILL_URLS:
            summary_url = f"{url}?summaryStartTimeInSeconds={start_epoch}&summaryEndTimeInSeconds={end_epoch}"
            res = oauth.get(url=summary_url)
            if res.status_code != 202:
                raise Exception(f"Invalid response for backfill url {summary_url}, got response response: {res.content},{res.status_code}")
            else:
                _LOGGER.info(f"Called backfill {summary_url}")

        time.sleep(BACKFILL_SLEEP_BETWEEN_CALLS)
        end_date = start_date
        start_date = start_date - timedelta(seconds=BACKFILL_SECONDS)


@task
def handle_summaries(request_body, summary_name, file_name, fields_to_remove=None):
    print(f"Handling summaries {summary_name}")
    try:
        summaries = extract_summaries(request_body, summary_name)

        grouped_summaries = group_summaries_per_user_and_per_month(summaries)
        print("Grouped summaries")
        for garmin_user_id, monthly_summaries in grouped_summaries.items():
            oh_user = get_oh_user_from_garmin_id(garmin_user_id)
            print("Got user")
            oh_user_data = api.exchange_oauth2_member(oh_user.get_access_token())
            print("Got user data")
            for month, summaries in monthly_summaries.items():
                remove_unwanted_fields(summaries, fields_to_remove)
                print(f"Uploading summaries for month {month}")
                upload_summaries_for_month(month, oh_user, oh_user_data, summaries, file_name)
                print(f"Uploaded summaries for month {month}")

            oh_user.garmin_member.last_updated = make_aware(datetime.utcnow(), timezone=timezone.utc)
            oh_user.garmin_member.save()
            print(f"Saved member")
        print(f"Handled summaries {len(summaries)} summaries {summary_name}")
    except:
        e = sys.exc_info()[0]
        # TODO: don't log personal user data
        _LOGGER.error(f"Failed to handle summaries JSON {summary_name} {request_body} {e}")
        traceback.print_exc()


def extract_summaries(request_body, summary_name):
    json_body = json.loads(request_body)
    summaries = json_body[summary_name]
    if not summaries:
        raise Exception(f'Could not find summaries with name {summary_name}')
    other_keys = [key for key in json_body.keys() if key != summary_name]
    if len(other_keys) > 0:
        logging.warning(f'Found ignored keys {other_keys} in summary file')
    return summaries
