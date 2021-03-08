from django.db import models

from openhumans.models import OpenHumansMember


class GarminMember(models.Model):
    """
    Store data for a Garmin Member.
    This is a one to one relationship with an OpenHumansMember object.
    """
    member = models.OneToOneField(OpenHumansMember, related_name="garmin_member", on_delete=models.CASCADE)
    userid = models.CharField(max_length=255, unique=True, null=True)  # user id that garmin health api uses
    access_token = models.CharField(max_length=512)  # oauth1 access token, valid as long as it's not revoked
    access_token_secret = models.CharField(max_length=512, null=True)
    last_updated = models.DateTimeField(null=True)
    has_health_export_permission = models.BooleanField(default=False)


class SummariesToProcess(models.Model):
    id = models.IntegerField(primary_key=True, auto_created=True)
    summaries_json = models.TextField()
    garmin_user_id = models.CharField(max_length=255, null=False)
    year_month = models.CharField(max_length=255, null=False)
