MAX_FILE_BYTES = 256000000  # 256 MB

GARMIN_HEALTH_API_TAG = 'garmin-health-api'

BACKFILL_MIN_YEAR = 2015  # that's when the smart watches with tracking capabilities came out
BACKFILL_SECONDS = 7776000  # Maximum allowed by the API
BACKFILL_SLEEP_BETWEEN_CALLS = 2

GARMIN_BACKFILL_URLS = [
    'https://healthapi.garmin.com/wellness-api/rest/backfill/dailies',
    # 'https://healthapi.garmin.com/wellness-api/rest/backfill/epochs',
    # 'https://healthapi.garmin.com/wellness-api/rest/backfill/sleeps',
    # 'https://healthapi.garmin.com/wellness-api/rest/backfill/bodyComps',
    # 'https://healthapi.garmin.com/wellness-api/rest/backfill/stressDetails',
    # 'https://healthapi.garmin.com/wellness-api/rest/backfill/userMetrics',
    # 'https://healthapi.garmin.com/wellness-api/rest/backfill/pulseOx',
    # 'https://healthapi.garmin.com/wellness-api/rest/backfill/respiration',
]
