from django.db.models import QuerySet
from django.http import HttpRequest

from django_otp.plugins.otp_static.lib import add_static_token
from django_otp.plugins.otp_static.models import StaticToken

from aidants_connect_web.admin import AidantAdmin


def add_static_token_for_aidants(self, request: HttpRequest, queryset: QuerySet):
    for aidant in queryset:
        if not StaticToken.objects.filter(device__user=aidant).exists():
            add_static_token(aidant.username, "123456")


AidantAdmin.add_static_token_for_aidants = add_static_token_for_aidants
AidantAdmin.add_static_token_for_aidants.short_description = "Ajouter des token infinis"
AidantAdmin.actions.append("add_static_token_for_aidants")
