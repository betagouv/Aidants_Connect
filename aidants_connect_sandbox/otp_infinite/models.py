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
                self.set_last_used_timestamp(commit=False)
                self.save()
            else:
                self.throttle_increment()
        else:
            match = None

        return match is not None



def ac_device_classes():
    """
    Returns an iterable of all loaded device models.
    """
    from django.apps import apps  # isort: skip
    from django_otp.models import Device

    for config in apps.get_app_configs():
        for model in config.get_models():
            if issubclass(model, Device):
                yield model


import django_otp
django_otp.device_classes = ac_device_classes

def extends_verify_token(self, token):
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

