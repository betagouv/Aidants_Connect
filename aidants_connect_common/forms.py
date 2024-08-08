import functools
from copy import deepcopy
from datetime import timedelta
from inspect import signature
from itertools import accumulate
from typing import Iterable, Tuple, Union

from django import forms
from django.conf import settings
from django.core import validators
from django.core.exceptions import NON_FIELD_ERRORS, ValidationError
from django.db.models import Model, QuerySet
from django.db.models.utils import AltersData
from django.forms import (
    BaseForm,
    BaseFormSet,
    BaseModelForm,
    BaseModelFormSet,
    BoundField,
    Field,
    Form,
    Media,
    MediaDefiningClass,
    RadioSelect,
    TypedChoiceField,
)
from django.forms.utils import ErrorList, pretty_name
from django.utils.datastructures import MultiValueDict
from django.utils.html import format_html
from django.utils.translation import ngettext

from dsfr.forms import DsfrBaseForm
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.phonenumber import to_python
from phonenumbers.phonenumber import PhoneNumber

from aidants_connect.utils import strtobool
from aidants_connect_common.models import Formation


class PatchedErrorList(ErrorList):
    """An ErrorList that will just print itself as a <p> when it has only 1 item"""

    template_name = template_name_ul = "forms/errors/list/ul.html"
    template_name_text = "forms/errors/list/text.txt"

    def __init__(self, initlist=None, error_class=None, renderer=None):
        super().__init__(initlist, error_class, renderer)
        self._error_codes = None

    @property
    def error_codes(self):
        if not self._error_codes:
            self._error_codes = [error.code for error in self.data]
        return self._error_codes

    def get_error_by_code(self, error_code):
        return next((error for error in self.data if error.code == error_code), None)


class WidgetAttrMixin:
    def widget_attrs(self, widget_name: str, attrs: dict):
        for attr_name, attr_value in attrs.items():
            self.fields[widget_name].widget.attrs[attr_name] = attr_value


class PatchedModelForm(forms.ModelForm, WidgetAttrMixin):
    def __init__(self, *args, **kwargs):
        sig = signature(super().__init__).bind_partial(*args, **kwargs)
        sig.arguments.setdefault("label_suffix", "")
        sig.arguments["error_class"] = PatchedErrorList

        super().__init__(*sig.args, **sig.kwargs)


class PatchedForm(forms.Form, WidgetAttrMixin):
    def __init__(self, *args, **kwargs):
        sig = signature(super().__init__).bind_partial(*args, **kwargs)
        sig.arguments.setdefault("label_suffix", "")
        sig.arguments["error_class"] = PatchedErrorList

        super().__init__(*sig.args, **sig.kwargs)


class ErrorCodesManipulationMixin:
    @property
    def errors_codes(self) -> dict[str, MultiValueDict[str, str]]:
        """
        Return a dict associating all the form's error codes with a dict associating the
        field names presenting these errors with a list of the error messages
        Exemple:
        >>> from django import forms
        >>> from aidants_connect_common.forms import ErrorCodesManipulationMixin
        >>> class TestForm(ErrorCodesManipulationMixin, forms.Form):
        ...     is_ok = forms.BooleanField()
        ...     name = forms.CharField()
        >>> form = TestForm()
        >>> form.errors_codes
        {'required': {'is_ok': ['Ce champ est obligatoire.'],'name': ['Ce champ est obligatoire.']}}
        """  # noqa: E501

        if not hasattr(self, "errors"):
            raise AttributeError(
                "ErrorCodesManipulationMixin must be used on Form class"
            )
        if not hasattr(self, "_errors_codes"):
            self._errors_codes: dict[str, MultiValueDict[str, str]] = {}
            for field, errors in self.errors.items():
                for error in errors.as_data():
                    code = error.code or ""
                    self._errors_codes.setdefault(code, MultiValueDict())
                    self._errors_codes[code].setlistdefault(field)
                    self._errors_codes[code].appendlist(field, error.message or "")
        return self._errors_codes


class AcPhoneNumberField(PhoneNumberField):
    """A PhoneNumberField which accepts any number from metropolitan France
    and overseas"""

    regions = settings.FRENCH_REGION_CODES

    def to_python(self, value: PhoneNumber | str):
        for region in self.regions:
            # value can be of type PhoneNumber in which case `to_python`
            # does not convert it again using the new region. We need
            # to force conversion of value to string here to ensure
            # the correct region is used.
            phone_number = to_python(f"{value}", region=region)

            if phone_number in validators.EMPTY_VALUES:
                return self.empty_value

            if phone_number and phone_number.is_valid():
                return phone_number

        raise ValidationError(self.error_messages["invalid"])


class FormationRegistrationForm(DsfrBaseForm):
    formations = forms.ModelMultipleChoiceField(queryset=Formation.objects.none())

    def __init__(self, attendant: Model, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["formations"].queryset = Formation.objects.available_for_attendant(
            timedelta(days=settings.TIMEDELTA_IN_DAYS_FOR_INSCRIPTION), attendant
        )


class FollowMyHabilitationRequesrForm(DsfrBaseForm):
    email = forms.EmailField(label="Adresse email")

    def clean_email(self):
        email = self.cleaned_data.get("email", None)

        from aidants_connect_habilitation.models import Issuer

        try:
            return Issuer.objects.get(email=email)
        except Issuer.DoesNotExist:
            raise ValidationError(
                "Il nʼexiste pas de demande dʼhabilitation associée à cet email. "
                "Veuillez vérifier votre saisie ou renseigner une autre adresse email."
            )


class CleanEmailMixin:
    def clean_email(self):
        return self.cleaned_data["email"].lower().strip()


class ConseillerNumerique(Form):
    conseiller_numerique = TypedChoiceField(
        label=format_html(
            'Fait partie du <a class="fr-link" href="{}">{}</a>',
            settings.CONSEILLER_NUMERIQUE_PAGE,
            "dispositif conseiller numérique",
        ),
        label_suffix=" :",
        choices=((True, "Oui"), (False, "Non")),
        coerce=lambda value: bool(strtobool(value)),
        widget=RadioSelect,
    )

    def clean(self):
        result = super().clean()
        result.setdefault("conseiller_numerique", None)
        result.setdefault("email", "")
        if result["conseiller_numerique"] is True and result["email"].endswith(
            settings.CONSEILLER_NUMERIQUE_EMAIL
        ):
            self.add_error(
                "email",
                (
                    "Suite à l'annonce de l'arrêt des adresses emails "
                    f"{settings.CONSEILLER_NUMERIQUE_EMAIL}"
                    " le 15 novembre 2024, nous vous invitons à renseigner"
                    " une autre adresse email nominative et professionnelle."
                ),
            )

        return result


FormLike = Union[BaseForm, BaseFormSet]
ModelFormLike = Union[BaseModelForm, BaseModelFormSet]


class DeclarativeFormMetaclass(MediaDefiningClass):
    def __new__(mcs, name, bases, attrs):
        attrs["declared_form_classes"] = {
            key: attrs.pop(key)
            for key, value in list(attrs.items())
            if isinstance(value, type) and issubclass(value, FormLike)
        }

        new_class = super().__new__(mcs, name, bases, attrs)

        # Walk through the MRO.
        declared_form_classes = {}
        for base in reversed(new_class.__mro__):
            # Collect fields from base class.
            if hasattr(base, "declared_form_classes"):
                declared_form_classes.update(base.declared_form_classes)

            # Field shadowing.
            for attr, value in base.__dict__.items():
                if value is None and attr in declared_form_classes:
                    declared_form_classes.pop(attr)

        new_class.base_form_casses = declared_form_classes

        return new_class


class BaseMultiForm(metaclass=DeclarativeFormMetaclass):
    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        initial=None,
        error_class=ErrorList,
        form_kwargs=None,
        renderer=None,
    ):
        self.is_bound = data is not None or files is not None
        self.prefix = prefix or self.get_default_prefix()
        self.auto_id = auto_id
        self.data = MultiValueDict() if data is None else data
        self.files = MultiValueDict() if files is None else files
        self.initial = initial or {}
        self.error_class = error_class or ErrorList
        self.form_kwargs = form_kwargs or {}
        self.renderer = renderer
        self._errors = None  # Stores the errors after clean() has been called.
        self.form_classes = deepcopy(self.base_form_casses)

        self._forms_cache = {}

    def __repr__(self):
        if self._errors is None:
            is_valid = "Unknown"
        else:
            is_valid = self.is_bound and not self._errors
        return (
            f"<{self.__class__.__name__} "
            f"bound={self.is_bound}, "
            f"valid={is_valid}, "
            f"form_classes={self.form_classes}>"
        )

    def __iter__(self) -> Iterable[FormLike]:
        for name in self.forms:
            yield self[name]

    def __getitem__(self, name) -> FormLike:
        try:
            return self.forms[name]
        except KeyError:
            raise KeyError(
                f"Key '{name}' not found in '{self.__class__.__name__}'. "
                f"Choices are: {', '.join(sorted(self.form_classes.keys()))}."
            )

    @property
    def forms(self) -> dict[str, FormLike]:
        if not self._forms_cache:
            for name in self.form_classes:
                self._forms_cache[name] = self.get_form(name)
        return self._forms_cache

    @classmethod
    def get_default_prefix(cls):
        return "multiform"

    def get_form(self, name):
        try:
            form_class = self.form_classes[name]
        except KeyError:
            raise KeyError(
                f"Key '{name}' not found in '{self.__class__.__name__}'. "
                f"Choices are: {', '.join(sorted(self.form_classes.values()))}."
            )
        return self._construct_form(
            name, form_class, **self.get_form_kwargs(name, form_class)
        )

    def get_form_kwargs(self, name, form_class):
        return self.form_kwargs.get(name, {}).copy()

    def _construct_form(self, name, form_class, **kwargs):
        """Instantiate and return the i-th form instance in a formset."""
        defaults = {
            "auto_id": self.auto_id,
            "prefix": self.add_prefix(name),
            "error_class": self.error_class,
            "renderer": self.renderer,
        }
        if self.is_bound:
            defaults["data"] = self.data
            defaults["files"] = self.files
        if self.initial and (initial := self.initial.get(name)):
            defaults["initial"] = initial

        defaults.update(kwargs)

        if issubclass(form_class, BaseFormSet):
            # renderer is not a constructor argument of formsets
            # It need to be processed differently
            renderer = defaults.pop("renderer", None)
            form = form_class(**defaults)
            if renderer:
                form.renderer = renderer
            return form

        return form_class(**defaults)

    def add_non_field_error(self, form: str | None, error: str | ValidationError):
        if not isinstance(error, ValidationError):
            error = ValidationError(error)

        if hasattr(error, "error_dict"):
            raise TypeError(
                "The `error` argument cannot contains errors for multiple fields."
            )

        form = form or NON_FIELD_ERRORS

        if form in self.forms and isinstance(self.forms[form], BaseFormSet):
            self.forms[form].non_form_errors().extend(error.error_list)
            self.errors.setdefault(NON_FIELD_ERRORS, {})
            self.errors[NON_FIELD_ERRORS].update(
                {form: self.forms[form].non_form_errors()}
            )
        elif form in self.forms:
            self.forms[form].add_error(None, error)
            self.errors.setdefault(form, self.forms[form].errors)
        elif form == NON_FIELD_ERRORS:
            self.errors.setdefault(NON_FIELD_ERRORS, {})
            self.errors[NON_FIELD_ERRORS].setdefault(
                NON_FIELD_ERRORS,
                self.error_class(error_class="nonfield", renderer=self.renderer),
            )
            self.errors[NON_FIELD_ERRORS][NON_FIELD_ERRORS].extend(error.error_list)
        else:
            raise ValueError(
                "'form' argument must be a form name present in "
                f"{self.form_classes.keys()} or None (was {form})"
            )

    def add_prefix(self, name):
        return "%s-%s" % (self.prefix, name)

    def is_valid(self):
        return self.is_bound and not self.errors

    @property
    def errors(self) -> dict[str, ErrorList | dict[str, ErrorList]] | None:
        """Return a list of form.errors for every form in self.forms."""
        if self._errors is None:
            self.full_clean()
        return self._errors

    def full_clean(self):
        self._errors = {}

        if not self.is_bound:  # Stop further processing.
            return

        for name, form in self.forms.items():
            if form.is_valid():
                if not hasattr(self, "cleaned_data"):
                    self.cleaned_data = {}
                self.cleaned_data[name] = form.cleaned_data
            else:
                if form.errors:
                    self._errors[name] = form.errors
                if isinstance(form, BaseFormSet) and form.non_form_errors():
                    self.errors.setdefault(NON_FIELD_ERRORS, {})
                    self.errors[NON_FIELD_ERRORS].update({name: form.non_form_errors()})

        try:
            self.clean()
        except ValidationError as e:
            self.add_non_field_error(None, e)

    def clean(self):
        pass

    @property
    def media(self):
        return accumulate((form.media for form in self), initial=Media())


class BaseModelMultiForm(BaseMultiForm, AltersData):
    def __init__(
        self,
        data=None,
        files=None,
        auto_id="id_%s",
        prefix=None,
        querysets: None | dict[str, QuerySet] = None,
        initial=None,
        error_class=ErrorList,
        form_kwargs=None,
        renderer=None,
    ):
        self.querysets = querysets or {}
        super().__init__(
            data, files, auto_id, prefix, initial, error_class, form_kwargs, renderer
        )

    def get_queryset(self, name) -> QuerySet:
        return self.querysets.get(name, None)

    def get_form_kwargs(self, name, form_class):
        kwargs = super().get_form_kwargs(name, form_class)
        queryset = self.get_queryset(name)
        if (
            "queryset" not in kwargs
            and queryset is not None
            and issubclass(self.form_classes[name], ModelFormLike)
        ):
            kwargs["queryset"] = queryset
        return kwargs

    @property
    def model_forms(self) -> Iterable[Tuple[str, ModelFormLike]]:
        for name, form in self.forms.items():
            if isinstance(form, ModelFormLike):
                yield name, form

    def save(self, commit=True):
        if self.errors:
            raise ValueError(
                ngettext(
                    "The form %s could not be saved because it has errors.",
                    "The forms %s could not be saved because it has errors.",
                    len(self.errors),
                )
                % (
                    list(self.errors.keys())[0]
                    if len(self.errors) == 1
                    else ", ".join(self.errors.keys())
                ),
            )

        return {name: form.save(commit) for name, form in self.model_forms}


class PropertyBoundField(BoundField):
    """Waiting for https://github.com/django/django/pull/18289 to be merged"""

    @property
    def label(self):
        return pretty_name(self.name) if self.field.label is None else self.field.label

    @label.setter
    def label(self, value):
        self.field.label = value

    @property
    def help_text(self):
        return self.field.help_text or ""

    @help_text.setter
    def help_text(self, value):
        self.field.help_text = value

    @property
    def renderer(self):
        return self.form.renderer

    @renderer.setter
    def renderer(self, value):
        self.form.renderer = value

    @property
    def html_name(self):
        return self.form.add_prefix(self.name)

    @html_name.setter
    def html_name(self, _):
        pass

    @property
    def html_initial_name(self):
        return self.form.add_initial_prefix(self.name)

    @html_initial_name.setter
    def html_initial_name(self, _):
        pass

    @property
    def html_initial_id(self):
        return self.form.add_initial_prefix(self.auto_id)

    @html_initial_id.setter
    def html_initial_id(self, _):
        pass


class CustomBoundFieldForm(forms.Form):
    """Waiting for https://github.com/django/django/pull/18266 to be merged"""

    bound_field_class = PropertyBoundField

    def __init__(self, *args, **kwargs):
        self.__fields = {}
        super().__init__(*args, **kwargs)

    @property
    def fields(self):
        return self.__fields

    @fields.setter
    def fields(self, value: dict[str, Field]):
        """
        Intercepts the self.fields initialisation in super().__init__()

        This is necessary because BaseForm makes a deepcopy of self.base_field during
        __init__ so we don't modify class-wide fields. We want to edit
        Field.get_bound_field as soon as possible.
        """
        for field in value.values():
            field.get_bound_field = functools.update_wrapper(
                functools.partial(
                    lambda _, name: self.bound_field_class(
                        self, self.__fields[name], name
                    )
                ),
                field.get_bound_field,
            )
        self.__fields = value
