from django.urls import path

from . import views
from .views import authorize_garmin, complete_garmin, garmin_deregistrations, garmin_user_permissions_change, garmin_body_composition, garmin_dailies, garmin_epochs, \
    garmin_pulse_ox, garmin_respiration, garmin_sleeps, garmin_stress, garmin_third_party_dailies, garmin_user_metrics

urlpatterns = [
    path('', views.index, name='index'),
    path('logout/?', views.logout_user, name='logout'),
    path('about/?', views.about, name='about'),

    path('garmin/authorize/', authorize_garmin, name='authorize-garmin'),
    path('garmin/complete/<str:resource_owner_secret>/', complete_garmin, name='authorize-garmin'),
    path('garmin-endpoint/deregistrations/', garmin_deregistrations, name='garmin-deregistrations'),
    path('garmin-endpoint/user-permissions-change/', garmin_user_permissions_change, name='garmin-user-permissions-change'),
    path('garmin-endpoint/body-composition/', garmin_body_composition, name='garmin-body-composition'),
    path('garmin-endpoint/dailies/', garmin_dailies, name='garmin-dailies'),
    path('garmin-endpoint/epochs/', garmin_epochs, name='garmin-epochs'),
    path('garmin-endpoint/pulse-ox/', garmin_pulse_ox, name='garmin-pulse-ox'),
    path('garmin-endpoint/respiration/', garmin_respiration, name='garmin-respiration'),
    path('garmin-endpoint/sleeps/', garmin_sleeps, name='garmin-sleeps'),
    path('garmin-endpoint/stress/', garmin_stress, name='garmin-stress'),
    path('garmin-endpoint/third-party-dailies/', garmin_third_party_dailies, name='garmin-third-party-dailies'),
    path('garmin-endpoint/user-metrics/', garmin_user_metrics, name='garmin-user-metrics'),
]