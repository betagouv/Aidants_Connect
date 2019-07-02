from django import forms
from aidants_connect_web.models import Usager, Mandat

DEMARCHES = (
    (
        "Logement",
        [
            ("chg_adresse", "Signaler un changement d’adresse"),
            ("alloc_logement", "Demander une allocation logement"),
            ("paiement_fact", "Demander une aide au paiement des factures"),
            (
                "renov_energ",
                "Demander une aide pour la rénovation énergétique de mon logement",
            ),
            ("heberg_social", "Hébergement social"),
            ("ehpad", "Ehpad"),
        ],
    ),
    (
        "Transport",
        [
            ("carte_grise", "Carte grise"),
            ("permis_conduire", "Permis de conduire"),
            ("infrac_route", "Infractions routières"),
        ],
    ),
    (
        "Santé",
        [
            ("affil_rembours_ss", "Affiliation ou remboursement sécurité sociale"),
            ("hospitalisation", "Hospitalisation"),
            ("soins_domicile", "Soins à domicile"),
            ("invalid_tempo", "Invalidité temporaire"),
            ("pension_invalid", "Pension d’invalidité"),
        ],
    ),
    (
        "Handicap",
        [
            ("alloc_handicap", "Allocations (AAH, AEEH, PCH)"),
            ("cmuc", "Couverture maladie universelle complémentaire (CMU-C)"),
            ("acs", "Aide au paiement d’une complémentaire santé (ACS)"),
        ],
    ),
    (
        "Aides sociales",
        [
            ("rsa", "Revenu de solidarité active (RSA)"),
            ("apa", "Allocation personnalisée d’autonomie (APA)"),
            ("aspa", "Allocation de solidarité aux personnes âgées (ASPA)"),
            ("asi", "Allocation supplémentaire d’invalidité (ASI)"),
            ("ass", "Allocation de solidarité spécifique (ASS)"),
            ("prime_activite", "Prime d’activité"),
            ("chq_energie", "Chèque énergie"),
            ("alloc_famille", "Allocation familiale"),
        ],
    ),
    (
        "Famille",
        [
            ("naissance", "Naissance"),
            ("adoption", "Adoption"),
            ("pacs", "Pacs"),
            ("mariage", "Mariage"),
            ("divorce", "Divorce"),
        ],
    ),
    (
        "Papiers",
        [
            ("cni", "Carte d’identité"),
            ("passeport", "Passeport"),
            ("certificat_docs", "Certificat, copie, légalisation de document"),
            ("livret_famille", "Livret de famille"),
            ("chg_nom", "Changement de nom ou prénom"),
            ("chg_sexe", "Changement de sexe"),
        ],
    ),
    ("Elections", [("inscrpt_listes", "S’inscrire sur les listes électorales")]),
    (
        "Impôts",
        [
            ("decl_revenus", "Déclaration de revenus"),
            ("impots_pro", "Impôts professionnels"),
            ("taxe_habit", "Taxe d’habitation"),
        ],
    ),
)


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
        choices=DEMARCHES, widget=forms.CheckboxSelectMultiple
    )

    duration = forms.CharField(required=True, initial=3)


class FCForm(forms.Form):
    given_name = forms.CharField(required=True, label="Prénom")
    family_name = forms.CharField(required=True, label="Nom de famille")


class RecapForm(forms.models.ModelForm):
    class Meta:
        model = Mandat
        fields = ("perimeter", "duration")

    personal_data = forms.BooleanField(required=True)
    brief = forms.BooleanField(required=True)
