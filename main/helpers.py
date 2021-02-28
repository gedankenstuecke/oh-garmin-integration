import json
import logging
import os
import tempfile
from collections import defaultdict
from datetime import datetime

import requests
from ohapi import api

from main.consts import MAX_FILE_BYTES, GARMIN_HEALTH_API_TAG
from main.models import GarminMember

epoch = datetime.utcfromtimestamp(0)

_LOGGER = logging.getLogger(__name__)


def unix_time_seconds(dt):
    return int((dt - epoch).total_seconds())


def write_json_data_to_tmp_file(filename, json_data):
    tmp_dir = tempfile.mkdtemp()
    full_path = os.path.join(tmp_dir, filename)
    with open(full_path, 'w') as json_file:
        json_file.write(json.dumps(json_data))
        json_file.flush()
    return full_path


def download_json_data(download_url):
    return json.loads(requests.get(download_url).content)


def find_existing_data_file(oh_user_data, file_name, month_name):
    for file in oh_user_data['data']:
        _LOGGER.info(f"Got file {file}")
        tags = file['metadata']['tags']
        if tags and GARMIN_HEALTH_API_TAG in tags and file_name in tags and month_name in tags:
            return file

    return None  # Not found


def merge_summaries(new_summaries, old_summaries):
    result = []
    seen_summary_ids = set()
    for summary in new_summaries + old_summaries:
        summary_id = summary['summaryId']
        if summary_id not in seen_summary_ids:
            result.append(summary)
            seen_summary_ids.add(summary_id)
    return result


def upload_summaries_for_month(month, oh_user, oh_user_data, summaries, file_name):
    existing_file = find_existing_data_file(oh_user_data, file_name, month)
    if existing_file:
        download_url = existing_file['download_url']
        old_summaries = download_json_data(download_url)
        summaries = merge_summaries(summaries, old_summaries)
    existing_file_id = existing_file['id'] if existing_file else None

    _LOGGER.info(f"Uploading {len(summaries)} summaries of type {file_name} for user {oh_user.oh_id} in month {month}")
    upload_summaries(oh_user, summaries, file_name, month, existing_file_id)


def remove_unwanted_fields(summaries, fields_to_remove):
    remove_fields(summaries, ['userId', 'userAccessToken'])  # No need to store this data in every single summary
    if fields_to_remove:
        remove_fields(summaries, fields_to_remove)


def remove_fields(summaries, fields_to_remove):
    for summary in summaries:
        for field in fields_to_remove:
            if field in summary:
                del summary[field]


def upload_summaries(oh_user, summaries, file_name, month, existing_file_id):
    fn = write_json_data_to_tmp_file(f'garmin-health-api-{file_name}-{month}.json', summaries)
    api.upload_aws(fn, create_metadata(file_name, month),
                   oh_user.get_access_token(),
                   project_member_id=oh_user.oh_id,
                   max_bytes=MAX_FILE_BYTES)
    if existing_file_id:
        api.delete_file(oh_user.get_access_token(), file_id=existing_file_id)


def get_django_user_id_from_garmin_id(garmin_user_id):
    oh_user = get_oh_user_from_garmin_id(garmin_user_id)
    return oh_user.user.id


def get_oh_user_from_garmin_id(garmin_user_id):
    garmin_member = GarminMember.objects.get(userid=garmin_user_id)
    return garmin_member.member


def create_metadata(summary_name, month_name):
    return {
        'description': f'Garmin Health API data {summary_name} {month_name}',
        'tags': [GARMIN_HEALTH_API_TAG, summary_name, month_name],
        'updated_at': str(datetime.utcnow()),
    }


def extract_timestamp(summary):
    if "startTimeInSeconds" in summary:
        # Used in almost all types of summaries
        return datetime.fromtimestamp(summary["startTimeInSeconds"])
    if "measurementTimeInSeconds" in summary:
        # Used for body composition
        return datetime.fromtimestamp(summary["measurementTimeInSeconds"])
    if "calendarDate" in summary:
        # Used for user metrics
        return datetime.strptime(summary['calendarDate'], '%Y-%m-%d')

    raise Exception(f"Failed to find timestamp field in summary. Found keys {summary.keys()}")


def group_summaries_per_user_and_per_month(summaries):
    result = defaultdict(lambda: defaultdict(lambda: []))

    for summary in summaries:
        garmin_user_id = summary['userId']
        month = month_name(extract_timestamp(summary))
        result[garmin_user_id][month].append(summary)

    return result


def month_name(timestamp):
    return timestamp.strftime("%Y-%m")
