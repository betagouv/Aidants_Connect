from pathlib import Path

from django import forms
from django.forms.renderers import DjangoTemplates
from django.utils.functional import cached_property

NO_VALUE = object()


def strtobool(val, default=NO_VALUE):
    val = str(val).lower()
    truthy = ("y", "yes", "t", "true", "on", "1")
    falsy = ("n", "no", "f", "false", "off", "0")
    if val in truthy:
        return True
    elif val in falsy:
        return False
    elif default is not NO_VALUE:
        return default
    else:
        raise ValueError(
            "Invalid boolean value %r, authorized values are %r and %r"
            % (val, truthy, falsy)
        )


class ACDjangoTemplates(DjangoTemplates):
    """Trick to get `django-template-partials` to work with for rendering API"""

    default_loaders = [
        (
            "django.template.loaders.cached.Loader",
            [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
        )
    ]

    @cached_property
    def engine(self):
        import dsfr

        return self.backend(
            {
                "APP_DIRS": False,
                "DIRS": [
                    Path(dsfr.__path__[0]).resolve() / self.backend.app_dirname,
                    Path(forms.__path__[0]).resolve() / self.backend.app_dirname,
                ],
                "NAME": "djangoforms",
                "OPTIONS": {
                    "loaders": [
                        (
                            "template_partials.loader.Loader",
                            self.default_loaders,
                        )
                    ]
                },
            }
        )
