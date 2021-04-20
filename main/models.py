from django.db import models

from openhumans.models import OpenHumansMember


class GarminMember(models.Model):
    """
    Store data for a Garmin Member.
    This is a one to one relationship with an OpenHumansMember object.
    """
    id = models.AutoField(primary_key=True)
    member = models.OneToOneField(OpenHumansMember, related_name="garmin_member", on_delete=models.CASCADE)
    userid = models.CharField(max_length=255, unique=True, null=True)  # user id that garmin health api uses
    access_token = models.CharField(max_length=512)  # oauth1 access token, valid as long as it's not revoked
    access_token_secret = models.CharField(max_length=512, null=True)
    last_updated = models.DateTimeField(null=True)
    has_health_export_permission = models.BooleanField(default=False)
    was_backfilled = models.BooleanField(default=False)


class SummariesToProcess(models.Model):
    id = models.AutoField(primary_key=True)
    summaries_json = models.TextField()
    garmin_user_id = models.CharField(max_length=255, null=False)
    file_name = models.CharField(max_length=255, null=False)


class RetrievedData(models.Model):
    id = models.AutoField(primary_key=True)
    member = models.ForeignKey(OpenHumansMember, on_delete=models.CASCADE)
    data_type = models.CharField(max_length=255, null=False)
    min_date = models.DateTimeField(null=False)
    max_date = models.DateTimeField(null=False)

    class Meta:
        indexes = [
            models.Index(fields=['member', 'data_type']),
        ]
