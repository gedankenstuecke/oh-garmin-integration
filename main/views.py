import json
import logging
import time

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import ImproperlyConfigured, ObjectDoesNotExist
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from openhumans.models import OpenHumansMember

from .garmin_health import GarminHealth
from .models import GarminMember, RetrievedData
from .tasks import handle_summaries_delayed

_LOGGER = logging.getLogger(__name__)


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
    if request.user.is_authenticated and request.user.openhumansmember.garmin_member and request.user.openhumansmember.garmin_member.userid:
        context['is_garmin_member'] = True
        retrieved_data = RetrievedData.objects.filter(member=request.user.openhumansmember)
        context['retrieved_data'] = retrieved_data
        context['has_data'] = len(retrieved_data) > 0

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
    garmin_member.was_backfilled = False
    garmin_member.save()

    return redirect('/')


def authorize_garmin(request):
    garmin = GarminHealth(settings.GARMIN_KEY, settings.GARMIN_SECRET)
    garmin.fetch_oauth_token()
    oauth_callback = request.build_absolute_uri(reverse(complete_garmin, kwargs={"resource_owner_secret": garmin.resource_owner_secret}))
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
        try:
            garmin_member = GarminMember.objects.get(userid=user_id)
            garmin_member.has_health_export_permission = 'HEALTH_EXPORT' in permissions
            garmin_member.save()
        except ObjectDoesNotExist:
            _LOGGER.info("Ignoring permission change for unknown user " + user_id)
    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_body_composition(request):
    handle_summaries_delayed(request.body, 'bodyComps', "body-composition")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_dailies(request):
    handle_summaries_delayed(request.body, 'dailies', "dailies", ['activityType'])  # We remove activityType to avoid confusion. It's a legacy field that always has the value 'WALKING'

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_epochs(request):
    handle_summaries_delayed(request.body, 'epochs', "epochs")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_pulse_ox(request):
    handle_summaries_delayed(request.body, 'pulseox', "pulse-ox")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_respiration(request):
    handle_summaries_delayed(request.body, 'allDayRespiration', "respiration")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_sleeps(request):
    handle_summaries_delayed(request.body, 'sleeps', "sleep")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_stress(request):
    handle_summaries_delayed(request.body, 'stressDetails', "stress")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_third_party_dailies(request):
    handle_summaries_delayed(request.body, 'thirdPartyDetails', "third-party")  # I (Koen) could not test this since I don't have this data... TODO!

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_user_metrics(request):
    handle_summaries_delayed(request.body, 'userMetrics', "user-metrics")

    return HttpResponse(status=200)
