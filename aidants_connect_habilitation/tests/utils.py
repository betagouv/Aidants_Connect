from functools import singledispatch
from importlib import import_module
from inspect import getmembers, isclass
from typing import Type, TypeVar

from django.forms import BaseModelFormSet, ModelForm

from factory.django import DjangoModelFactory

from aidants_connect_habilitation.tests import factories


@singledispatch
def get_form(form_cls, ignore_errors=False, **kwargs):
    """
    Generates a form ModelForm or FormSet[ModelForm] populated with data.

    In order to correctly perform, the form class you pass as the form_cls
    parameter needs to inherit from ModelForm or FormSet[ModelForm].
    The ModelForm needs to map to a django Model that has a corresponding
    factory in aidants_connect_habilitation.tests.factories.

    For instance:

        # In models.py
        from django.db import models
        from django.utils.timezone import now


        class TestModel(models.Model):
            created = models.DateTimeField(default=now)


        # In forms.py
        from django import forms
        from aidants_connect_habilitation.models import TestModel

        class TestForm(forms.ModelForm):
            class Meta:
                model = TestModel

        # in aidants_connect_habilitation/tests/factories.py
        from factory.django import DjangoModelFactory
        from aidants_connect_habilitation.models import TestModel

        class TestFactory(DjangoModelFactory)
            class Meta:
                model = TestModel

        # Usage
        form = get_form(TestForm)

    This function will pick to the first factory in factory.py that has
    the same model as the form requested and build a form using the data
    generated from that factory.

    By default, it tries to generate valid froms but if your purpose is
    to generate forms with invalid data, you can skip error checking by
    setting the ignore_errors parameter to True.

    You can also directly pass data to the factory using **kwargs.

    :param form_cls: The form class to instanciate
    :param ignore_errors: If set to True get_form() won't perform an is_valid()
                          call on the generated form.
    :param kwargs: Supplementary arguments to pass to the factory.
    :return: The form to generate. Will be an instance of class form_cls.
    """
    raise NotImplementedError(
        f"{get_form.__name__} is not implemented for type {type(form_cls)}"
    )


T = TypeVar("T", bound=ModelForm)


@get_form.register(type(ModelForm))
def _(form_cls: Type[T], ignore_errors=False, **kwargs) -> T:
    form = form_cls(data=__get_form_data(form_cls, **kwargs))

    if not ignore_errors and not form.is_valid():
        raise ValueError(str(form.errors))

    return form


@get_form.register(type(BaseModelFormSet))
def _(
    form_cls: Type[BaseModelFormSet], ignore_errors=False, **kwargs
) -> BaseModelFormSet:
    formset_cls = form_cls
    form_cls = form_cls.form

    # BaseModelFormSet won't take `initial` in account unless
    # `extra` class property matches initial data length.
    # See https://docs.djangoproject.com/fr/4.0/topics/forms/modelforms/#s-id2 # noqa
    old_extra = formset_cls.extra
    formset_cls.extra = 10
    form: BaseModelFormSet = formset_cls(
        initial=[__get_form_data(form_cls, **kwargs) for _ in range(10)]
    )

    data = {
        "form-TOTAL_FORMS": f"{len(form)}",
        "form-INITIAL_FORMS": "0",
        "form-MIN_NUM_FORMS": "",
        "form-MAX_NUM_FORMS": "",
    }

    for i, subform in enumerate(form.forms):
        subform = form_cls(data=subform.initial)
        subform.is_valid()
        subdata = {f"form-{i}-{k}": v for (k, v) in subform.clean().items()}
        data.update(subdata)

    form = formset_cls(data=data)

    if not ignore_errors and not form.is_valid():
        raise ValueError(str(form.errors))

    formset_cls.extra = old_extra

    return form


def __get_form_data(form_cls: Type[T], **kwargs) -> T:
    for name, cls in getmembers(import_module(factories.__name__), isclass):
        if (
            issubclass(cls, DjangoModelFactory)
            and cls._meta.model == form_cls._meta.model
        ):
            factory_cls: Type[DjangoModelFactory] = cls
            break
    else:
        raise RuntimeError(
            f"No factory declared in {factories.__name__} with model of type "
            f"{form_cls}"
        )

    return form_cls(instance=factory_cls.build(**kwargs)).initial
