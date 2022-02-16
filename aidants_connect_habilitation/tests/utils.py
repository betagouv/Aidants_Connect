from functools import singledispatch
from importlib import import_module
from inspect import getmembers, isclass
from typing import Type, TypeVar

from django.forms import BaseFormSet, ModelForm

from factory.django import DjangoModelFactory

from aidants_connect_habilitation.tests import factories


@singledispatch
def get_form(form_cls, **kwargs):
    raise NotImplementedError(
        f"{get_form.__name__} is not implemented for type {type(form_cls)}"
    )


T = TypeVar("T", bound=ModelForm)


@get_form.register(type(ModelForm))
def _(form_cls: Type[T], **kwargs) -> T:
    form = form_cls(data=__get_form_data(form_cls, **kwargs))

    if not form.is_valid():
        raise ValueError(str(form.errors))

    return form


@get_form.register(type(BaseFormSet))
def _(form_cls: Type[BaseFormSet], **kwargs) -> BaseFormSet:
    formset_cls = form_cls
    form_cls = form_cls.form
    form: BaseFormSet = formset_cls(
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

    if not form.is_valid():
        raise ValueError(str(form.errors))

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
