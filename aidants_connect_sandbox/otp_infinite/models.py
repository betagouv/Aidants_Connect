from django.conf import settings

from django_otp.plugins.otp_static.models import StaticDevice


class AidantConnectStaticDevice(StaticDevice):
    class Meta:
        proxy = True

    def verify_token(self, token):
        if not settings.ACTIVATE_INFINITY_TOKEN:
            return False
        verify_allowed, _ = self.verify_is_allowed()
        if verify_allowed:
            match = self.token_set.filter(token=token).first()
            if match is not None:
                self.throttle_reset()
            else:
                self.throttle_increment()
        else:
            match = None

        return match is not None
