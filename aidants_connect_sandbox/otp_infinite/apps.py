from django.apps import AppConfig


class AidantsConnectSandboxOtpInfiniteConfig(AppConfig):
    name = "aidants_connect_sandbox.otp_infinite"

    def ready(self):
        from django_otp.plugins.otp_static.models import StaticDevice
        from .models import extends_verify_token
        StaticDevice.verify_token = extends_verify_token