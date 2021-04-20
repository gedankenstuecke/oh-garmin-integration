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


def find_existing_data_file(oh_user_data, file_name):
    for file in oh_user_data['data']:
        tags = file['metadata']['tags']
        if tags and GARMIN_HEALTH_API_TAG in tags and file_name in tags:
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


def merge_with_existing_and_upload(oh_user, summaries, file_name):
    access_token = oh_user.get_access_token()
    oh_user_data = api.exchange_oauth2_member(access_token)
    existing_file = find_existing_data_file(oh_user_data, file_name)
    if existing_file:
        download_url = existing_file['download_url']
        old_summaries = json.loads(requests.get(download_url).content)
        summaries = merge_summaries(summaries, old_summaries)
    existing_file_id = existing_file['id'] if existing_file else None

    _LOGGER.info(f"Uploading {len(summaries)} summaries to file {file_name} for user {oh_user.oh_id}")
    upload_summaries(oh_user, summaries, file_name, existing_file_id)

    return summaries


def remove_unwanted_fields(summaries):
    remove_fields(summaries, ['userId', 'userAccessToken'])  # No need to store this data in every single summary


def remove_fields(summaries, fields_to_remove):
    for summary in summaries:
        for field in fields_to_remove:
            if field in summary:
                del summary[field]


def upload_summaries(oh_user, summaries, file_name, existing_file_id):
    fn = write_json_data_to_tmp_file(f'garmin-health-api-{file_name}.json', summaries)
    api.upload_aws(fn, create_metadata(file_name), oh_user.get_access_token(), project_member_id=oh_user.oh_id, max_bytes=MAX_FILE_BYTES)
    if existing_file_id:
        api.delete_file(oh_user.get_access_token(), file_id=existing_file_id)


def get_django_user_id_from_garmin_id(garmin_user_id):
    oh_user = get_oh_user_from_garmin_id(garmin_user_id)
    return oh_user.user.id


def get_oh_user_from_garmin_id(garmin_user_id):
    garmin_member = GarminMember.objects.get(userid=garmin_user_id)
    return garmin_member.member


def create_metadata(file_name):
    return {
        'description': f'Garmin Health API data {file_name}',
        'tags': [GARMIN_HEALTH_API_TAG, file_name],
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


def extract_summaries(request_body, summary_name):
    json_body = json.loads(request_body)
    if summary_name not in json_body:
        raise Exception(f'Could not find summaries with name {summary_name}')

    summaries = json_body[summary_name]
    other_keys = [key for key in json_body.keys() if key != summary_name]
    if len(other_keys) > 0:
        logging.warning(f'Found ignored keys {other_keys} in summary file')
    return summaries


def summaries_to_process_key(summaries_to_process):
    return f"{summaries_to_process.garmin_user_id}_{summaries_to_process.file_name}"


def remove_all_oh_data_files_for_user(garmin_user_id):
    oh_user = get_oh_user_from_garmin_id(garmin_user_id)
    oh_user_data = api.exchange_oauth2_member(oh_user.get_access_token())
    for file in oh_user_data['data']:
        _LOGGER.info(f"Removing file {file}")
        api.delete_file(oh_user.get_access_token(), file_id=file['id'])
