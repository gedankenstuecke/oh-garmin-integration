import json
import logging
import sys
import time
import traceback
from datetime import datetime, timedelta, timezone

from celery.decorators import task
from django.conf import settings
from django.db import transaction
from django.utils.timezone import make_aware
from ohapi import api
from requests_oauthlib import OAuth1Session

from .consts import BACKFILL_SECONDS, BACKFILL_MIN_YEAR, GARMIN_BACKFILL_URLS, BACKFILL_SLEEP_BETWEEN_CALLS
from .helpers import unix_time_seconds, upload_summaries_for_month, group_summaries_per_user_and_per_month, get_oh_user_from_garmin_id, remove_unwanted_fields
from .models import GarminMember, SummariesToProcess

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

    print(f"Executing backfill for user ${get_oh_user_from_garmin_id(garmin_user_id)}")
    while start_date.year >= BACKFILL_MIN_YEAR:

        start_epoch = unix_time_seconds(start_date)
        end_epoch = unix_time_seconds(end_date)

        for url in GARMIN_BACKFILL_URLS:
            summary_url = f"{url}?summaryStartTimeInSeconds={start_epoch}&summaryEndTimeInSeconds={end_epoch}"
            res = oauth.get(url=summary_url)
            if res.status_code != 202:
                raise Exception(f"Invalid response for backfill url {summary_url}, got response response: {res.content},{res.status_code}")
            else:
                print(f"Called backfill {summary_url}")

        time.sleep(BACKFILL_SLEEP_BETWEEN_CALLS)
        end_date = start_date
        start_date = start_date - timedelta(seconds=BACKFILL_SECONDS)


@task
@transaction.atomic
def handle_summaries(garmin_user_id, year_month, file_name):
    print(f"Handling summaries for garmin_user_id={garmin_user_id}, year_month={year_month}, file_name={file_name}")
    try:
        summaries_to_process = SummariesToProcess.objects.get(garmin_user_id__exact=garmin_user_id, year_month__exact=year_month)
        if len(summaries_to_process) == 0:
            print("Nothing to do")
            return

        summaries = []
        for summaries_to_process in summaries_to_process:
            summaries.append(json.loads(summaries_to_process.summaries_json))

        oh_user = get_oh_user_from_garmin_id(garmin_user_id)
        print("Got user")
        oh_user_data = api.exchange_oauth2_member(oh_user.get_access_token())
        print("Got user data")
        print(f"Uploading summaries for month {year_month}")
        upload_summaries_for_month(year_month, oh_user, oh_user_data, summaries, file_name)
        print(f"Uploaded summaries for month {year_month}")

        oh_user.garmin_member.last_updated = make_aware(datetime.utcnow(), timezone=timezone.utc)
        oh_user.garmin_member.save()
        print(f"Saved member")
        print(f"Handled summaries {len(summaries)} summaries {file_name}")

        summaries_to_process.delete()

    except:
        e = sys.exc_info()[0]
        _LOGGER.error(f"Failed to handle summaries JSON {file_name} {e}")
        traceback.print_exc()
