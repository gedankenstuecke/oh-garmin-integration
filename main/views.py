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

from .garmin_health import GarminHealth
from .models import GarminMember
from .tasks import handle_backfill, handle_dailies

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
    # if request.user.is_authenticated:
    # context['overland_file'] = get_overland_file(request.user.openhumansmember)
    # context['overland_endpoint'] = urllib.parse.urljoin(settings.OPENHUMANS_APP_BASE_URL, request.user.openhumansmember.garminuser.endpoint_token + "/")
    if request.user.is_authenticated and request.user.openhumansmember.garmin_member:
        context['is_garmin_member'] = True

        # member= GarminMember.objects.get(oh_member_id=request.user.openhumansmember.)
        # print(f"queueing backfill ${request.user.openhumansmember.garmin_member.userid}")
        # handle_backfill(request.user.openhumansmember.garmin_member.userid)
    # print(current_app.tasks.keys())

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
    userid = garmin.api_id

    if hasattr(request.user.openhumansmember, 'garmin_member'):
        garmin_member = request.user.openhumansmember.garmin_member
    else:
        garmin_member = GarminMember()

    garmin_member.access_token = access_token
    garmin_member.access_token_secret = garmin.oauth.token.get('oauth_token_secret')
    garmin_member.userid = userid
    garmin_member.member = request.user.openhumansmember
    handle_backfill.delay(userid)
    garmin_member.save()
    if garmin_member:
        messages.info(request, "Your Garmin account has been connected.")
        return redirect('/')

    messages.warning(request, ("Something went wrong, please try connecting your "
                               "Garmin account again."))
    return redirect('/')


def authorize_garmin(request):
    print(request.user.openhumansmember)
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
    tmp_file = f"/tmp/garmin_body_composition_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_body_composition to {tmp_file}")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_dailies(request):
    tmp_file = f"/tmp/garmin_dailies_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_dailies to {tmp_file}")

    # TODO: call async
    handle_dailies(json.loads(request.body))

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_epochs(request):
    tmp_file = f"/tmp/garmin_epochs_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_epochs to {tmp_file}")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_pulse_ox(request):
    tmp_file = f"/tmp/garmin_pulse_ox_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_pulse_ox to {tmp_file}")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_respiration(request):
    tmp_file = f"/tmp/garmin_respiration_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_respiration to {tmp_file}")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_sleeps(request):
    tmp_file = f"/tmp/garmin_sleeps_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_sleeps to {tmp_file}")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_stress(request):
    tmp_file = f"/tmp/garmin_stress_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_stress to {tmp_file}")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_third_party_dailies(request):
    tmp_file = f"/tmp/garmin_third_party_dailies_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_third_party_dailies to {tmp_file}")

    return HttpResponse(status=200)


@csrf_exempt
@require_http_methods(["POST"])
def garmin_user_metrics(request):
    tmp_file = f"/tmp/garmin_user_metrics_{time.time()}"
    f = open(tmp_file, "ab")
    f.write(request.body)
    f.close()
    print(f"Saved garmin_user_metrics to {tmp_file}")

    return HttpResponse(status=200)
