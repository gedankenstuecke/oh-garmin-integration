import json
import os
import tempfile
from datetime import datetime, timedelta
from django.conf import settings
import requests

epoch = datetime.utcfromtimestamp(0)


def unix_time_seconds(dt):
    return int((dt - epoch).total_seconds())


def write_jsonfile_to_tmp_dir(filename, json_data):
    tmp_dir = tempfile.mkdtemp()
    full_path = os.path.join(tmp_dir, filename)
    with open(full_path, 'w') as json_file:
        json_file.write(json.dumps(json_data))
        json_file.flush()
    return full_path


def download_to_json(download_url):
    return json.loads(requests.get(download_url).content)
