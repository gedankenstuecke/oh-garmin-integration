import json
import logging
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import ImproperlyConfigured
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from openhumans.models import OpenHumansMember

from .consts import GARMIN_HEALTH_API_TAG
from .garmin_health import GarminHealth
from .helpers import extract_summaries, remove_fields, group_summaries_per_user_and_per_month, get_oh_user_from_garmin_id
from .models import GarminMember, SummariesToProcess
from .tasks import handle_backfill, handle_summaries

_LOGGER = logging.getLogger(__name__)

from ohapi import api


def index(request):
    """
    Starting page for app.
    """
    context = {}
    try:
        auth_url = OpenHumansMember.get_auth_url()
        context['auth_url'] = auth_url
    except ImproperlyConfigured as e:
        messages.info(request, mark_safe(f'<b>Received an error ${e}. You might to set up your ".env" file?</b>'))
    # if request.user.is_authenticated:
    # context['overland_file'] = get_overland_file(request.user.openhumansmember)
    # context['overland_endpoint'] = urllib.parse.urljoin(settings.OPENHUMANS_APP_BASE_URL, request.user.openhumansmember.garminuser.endpoint_token + "/")
    if request.user.is_authenticated and request.user.openhumansmember.garmin_member:
        context['is_garmin_member'] = True

        # member= GarminMember.objects.get(oh_member_id=request.user.openhumansmember.)
        # print(f"queueing backfill ${request.user.openhumansmember.garmin_member.userid}")
        # handle_backfill(request.user.openhumansmember.garmin_member.userid)
    # print(current_app.tasks.keys())
    # handle_summaries('4d866463-8368-41d0-8b8a-07595717ab91', '2021-02', 'user-metrics')

    return render(request, 'main/index.html', context=context)


def about(request):
    """
    give FAQ and further details on the app
    """
    return render(request, 'main/about.html')


def logout_user(request):
    """
    Logout user
    """
    if request.method == 'POST':
        logout(request)
    redirect_url = settings.LOGOUT_REDIRECT_URL
    return redirect(redirect_url)


def complete_garmin(request, resource_owner_secret):
    authorization_response = settings.OPENHUMANS_APP_BASE_URL + request.get_full_path()
    garmin = GarminHealth(settings.GARMIN_KEY, settings.GARMIN_SECRET)
    # oauth1 leg 3
    garmin.complete_garmin(authorization_response, resource_owner_secret)
    access_token = garmin.uat
    garmin_user_id = garmin.api_id

    if hasattr(request.user.openhumansmember, 'garmin_member'):
        garmin_member = request.user.openhumansmember.garmin_member
    else:
        garmin_member = GarminMember()

    garmin_member.access_token = access_token
    garmin_member.access_token_secret = garmin.oauth.token.get('oauth_token_secret')
    garmin_member.userid = garmin_user_id
    garmin_member.member = request.user.openhumansmember
    handle_backfill.delay(garmin_user_id)
    garmin_member.save()
    if garmin_member:
        messages.info(request, "Your Garmin account has been connected.")
        return redirect('/')

    messages.warning(request, ("Something went wrong, please try connecting your "
                               "Garmin account again."))
    return redirect('/')


def authorize_garmin(request):
    garmin = GarminHealth(settings.GARMIN_KEY, settings.GARMIN_SECRET)
    # oauth1 leg 1
    garmin.fetch_oauth_token()
    oauth_callback = request.build_absolute_uri(reverse(complete_garmin, kwargs={"resource_owner_secret": garmin.resource_owner_secret}))
    # oauth1 leg 2
    authorization_url = garmin.fetch_authorization_url(oauth_callback)

    return redirect(authorization_url)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_deregistrations(request):
    tmp_file = f"/tmp/garmin_deregistrations_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_deregistrations to {tmp_file}")


@csrf_exempt
@require_http_methods(["POST"])
def garmin_user_permissions_change(request):
    print("Garmin user permissions change " + str(request.body))
    data = json.loads(request.body)
    for user_permissions_change in data['userPermissionsChange']:
        user_id = user_permissions_change['userId']
        permissions = user_permissions_change['permissions']
        garmin_member = GarminMember.objects.get(userid=user_id)
        garmin_member.has_health_export_permission = 'HEALTH_EXPORT' in permissions
        garmin_member.save()

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_body_composition(request):
    handle_summary_delayed(request.body, 'bodyComps', "body-composition")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_dailies(request):
    handle_summary_delayed(request.body, 'dailies', "dailies", ['activityType'])  # We remove activityType to avoid confusion. It's a legacy field that always has the value 'WALKING'

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_epochs(request):
    handle_summary_delayed(request.body, 'epochs', "epochs")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_pulse_ox(request):
    handle_summary_delayed(request.body, 'pulseox', "pulse-ox")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_respiration(request):
    handle_summary_delayed(request.body, 'allDayRespiration', "respiration")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_sleeps(request):
    handle_summary_delayed(request.body, 'sleeps', "sleep")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_stress(request):
    handle_summary_delayed(request.body, 'stressDetails', "stress")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_third_party_dailies(request):
    handle_summary_delayed(request.body, 'thirdPartyDetails', "third-party")  # I (Koen) could not test this since I don't have this data... TODO!

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_user_metrics(request):
    handle_summary_delayed(request.body, 'userMetrics', "user-metrics")

    return HttpResponse(status=200)


def handle_summary_delayed(body, summaries_name, data_type, fields_to_remove=[]):
    body = body.decode('utf-8')
    summaries = extract_summaries(body, summaries_name)
    if fields_to_remove:
        remove_fields(summaries, fields_to_remove)
    grouped_summaries = group_summaries_per_user_and_per_month(summaries)
    for garmin_user_id, monthly_summaries in grouped_summaries.items():
        for year_month, summaries in monthly_summaries.items():
            _LOGGER.info(f"Saving summaries {data_type} for user {garmin_user_id} and month {year_month} for further processing")
            summaries_to_process = SummariesToProcess()
            summaries_to_process.summaries_json = json.dumps(summaries)
            summaries_to_process.garmin_user_id = garmin_user_id
            summaries_to_process.year_month = year_month
            summaries_to_process.data_type = data_type
            summaries_to_process.save()
            handle_summaries.delay(garmin_user_id, year_month, data_type)
