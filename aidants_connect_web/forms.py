from django import forms
from aidants_connect_web.models import Usager, Mandat
from django.conf import settings


class UsagerForm(forms.models.ModelForm):
    class Meta:
        model = Usager
        fields = (
            "given_name",
            "family_name",
            "preferred_username",
            "birthdate",
            "gender",
            "birthplace",
            "birthcountry",
            "email",
        )
        labels = {
            "given_name": "Prénoms",
            "family_name": "Nom de naissance",
            "preferred_username": "Nom d'usage (facultatif)",
            "birthdate": "Date de naissance (AAAA-MM-JJ)",
            "gender": "Genre",
            "birthplace": "Commune de naissance (Code INSEE)",
            "birthcountry": "Pays de naissance (Code INSEE)",
            "email": "Email",
        }
        widgets = {
            "given_name": forms.TextInput(
                attrs={
                    "placeholder": "Exemple : Camille-Marie Claude",
                    "value": "Éric Julien",
                }
            ),
            "family_name": forms.TextInput(
                attrs={"placeholder": "Exemple : Petit-Richard", "value": "MERCIER"}
            ),
            "preferred_username": forms.TextInput(
                attrs={"placeholder": "Exemple : Bernard", "value": "MERCIER"}
            ),
            "birthdate": forms.fields.DateInput(
                format="%Y-%m-%d", attrs={"value": "1969-03-17"}
            ),
            "birthplace": forms.fields.TextInput(
                attrs={"placeholder": "Code INSEE de la commune", "value": "95277"}
            ),
            "email": forms.fields.EmailInput(attrs={"value": "user@user.user"}),
        }
        error_messages = {
            "given_name": {
                "required": "Le champs Prénoms est obligatoire. "
                "Ex : Camille-Marie Claude Dominique"
            }
        }


class MandatForm(forms.Form):
    perimeter = forms.MultipleChoiceField(
        choices=settings.DEMARCHES, widget=forms.CheckboxSelectMultiple
    )

    duration = forms.CharField(required=True, initial=3)


class FCForm(forms.Form):
    given_name = forms.CharField(required=True, label="Prénom")
    family_name = forms.CharField(required=True, label="Nom de famille")
