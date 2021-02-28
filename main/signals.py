from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import GarminMember


@receiver(user_logged_in)
def create_garmin_member(sender, request, user, **kwargs):
    GarminMember.objects.get_or_create(member=user.openhumansmember)
