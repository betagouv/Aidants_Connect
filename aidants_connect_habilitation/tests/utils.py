from functools import singledispatch
from importlib import import_module
from inspect import getmembers, isclass
from json import dumps, loads
from pathlib import Path
from typing import Type, TypeVar, Union

from django.forms import BaseModelFormSet, ModelForm, model_to_dict
from django.forms.formsets import (
    INITIAL_FORM_COUNT,
    MAX_NUM_FORM_COUNT,
    MIN_NUM_FORM_COUNT,
    TOTAL_FORM_COUNT,
    ManagementForm,
)
from django.forms.models import fields_for_model

from factory.django import DjangoModelFactory

from aidants_connect_habilitation.tests import factories

MF = TypeVar("MF", bound=ModelForm)
BMFS = TypeVar("BMFS", bound=BaseModelFormSet)
T = TypeVar("T", bound=Union[ModelForm, BaseModelFormSet])


@singledispatch
def get_form(
    form_cls: Type[T],
    ignore_errors: bool = False,
    form_init_kwargs: dict = None,
    **kwargs,
) -> T:
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

    When using this function on a BaseModelFormSet, by default, 10 subforms
    will be generated. You can use the parameter ``form_init_kwargs`` to
    change this behaviour by passing ``{"initial": 5}``.

    You can also directly pass data to the factory using **kwargs.
    :param form_cls: The form class to instanciate
    :param ignore_errors: If set to True get_form() won't perform an is_valid()
                          call on the generated form.
    :param form_init_kwargs: supplementary keyword argument to pass to the form
                             constructor. You can pass ``{"initial": 5}`` to get
                             5 subforms when instanciating a BaseModelFormSet.
    :param kwargs: Supplementary arguments to pass to the factory.
    :return: The form to generate. Will be an instance of class form_cls.
    """
    raise NotImplementedError(
        f"{get_form.__name__} is not implemented for type {type(form_cls)}"
    )


@get_form.register(type(ModelForm))
def _(
    form_cls: Type[MF], ignore_errors=False, form_init_kwargs: dict = None, **kwargs
) -> MF:
    form_init_kwargs = form_init_kwargs or {}
    form = form_cls(
        data=__get_form_data(form_cls, form_init_kwargs, **kwargs), **form_init_kwargs
    )

    if not ignore_errors and not form.is_valid():
        raise ValueError(str(form.errors))

    return form


@get_form.register(type(BaseModelFormSet))
def _(
    form_cls: Type[BMFS],
    ignore_errors=False,
    form_init_kwargs: dict = None,
    **kwargs,
) -> BMFS:
    formset_cls = form_cls
    form_cls = form_cls.form

    form_init_kwargs = form_init_kwargs or {}
    formset_extra = form_init_kwargs.pop("initial", 10)

    old_extra = formset_cls.extra
    formset_cls.extra = formset_extra

    form: BaseModelFormSet = formset_cls(**form_init_kwargs)
    management_form = ManagementForm(auto_id=form.auto_id, prefix=form.prefix)

    data = {
        f"{management_form.add_prefix(k)}": v
        for k, v in {
            TOTAL_FORM_COUNT: formset_extra,
            INITIAL_FORM_COUNT: min(0, form.min_num),
            MIN_NUM_FORM_COUNT: form.min_num,
            MAX_NUM_FORM_COUNT: form.max_num,
        }.items()
    }

    for i in range(0, formset_extra):
        subform_data = __get_form_data(
            form_cls, {**form_init_kwargs, "prefix": form.add_prefix(i)}, **kwargs
        )
        data.update(**subform_data)

    formset_cls.extra = old_extra

    form = formset_cls(**form_init_kwargs, data=data)

    if not ignore_errors and not form.is_valid():
        raise ValueError(
            f"Errors: {form.errors}, non_form_errors: {form.non_form_errors()}"
        )

    return form


def __get_form_data(form_cls: Type[MF], form_init_kwargs: dict, **kwargs) -> dict:
    # Find factory from model class
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

    # Obtain the fields to serialize from form
    # This code was extracted from django.form.models
    form: MF = form_cls(**form_init_kwargs)
    fields = fields_for_model(
        form._meta.model,
        form._meta.fields,
        form._meta.exclude,
        form._meta.widgets,
        getattr(form, "formfield_callback", None),
        form._meta.localized_fields,
        form._meta.labels,
        form._meta.help_texts,
        form._meta.error_messages,
        form._meta.field_classes,
        apply_limit_choices_to=False,
    )

    # Serialize generated model to dict
    data = model_to_dict(factory_cls.build(**kwargs), fields=fields)

    return (
        {form.add_prefix(k): v for k, v in data.items()}
        if form_init_kwargs.get("prefix")
        else data
    )


def load_json_fixture(name: str, as_string=False) -> dict:
    path = Path(__file__).parent / "fixtures" / name
    with open(path) as f:
        result = loads(f.read())
        return dumps(result) if as_string else result
