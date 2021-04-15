import logging
from datetime import date, timedelta
from typing import Collection

from django.conf import settings
from django.contrib import messages as django_messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.utils import timezone, formats
from django.contrib.staticfiles import finders

from aidants_connect_web.decorators import activity_required, user_is_aidant
from aidants_connect_web.forms import MandatForm, RecapMandatForm, PatchedErrorList
from aidants_connect_web.models import (
    Autorisation,
    Connection,
    Journal,
    Mandat,
    Usager,
    Aidant,
)
from aidants_connect_web.utilities import (
    generate_attestation_hash,
    generate_qrcode_png,
    generate_mailto_link,
)
from aidants_connect_web.views.service import humanize_demarche_names

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


@login_required
@user_is_aidant
@activity_required
def new_mandat(request):
    aidant = request.user
    form = MandatForm()

    if request.method == "GET":
        return render(
            request,
            "aidants_connect_web/new_mandat/new_mandat.html",
            {"aidant": aidant, "form": form},
        )

    else:
        form = MandatForm(request.POST, error_class=PatchedErrorList)

        if form.is_valid():
            data = form.cleaned_data

            kwargs = {
                "aidant": request.user,
                "demarches": data["demarche"],
                "duree_keyword": data["duree"],
                "mandat_is_remote": data["is_remote"],
            }

            if kwargs["mandat_is_remote"] is True:
                kwargs["user_phone"] = data["user_phone"]

            connection = Connection.objects.create(**kwargs)
            request.session["connection"] = connection.pk
            return redirect("fc_authorize")
        else:
            return render(
                request,
                "aidants_connect_web/new_mandat/new_mandat.html",
                {"aidant": aidant, "form": form},
            )


@login_required
@user_is_aidant
@activity_required
def new_mandat_recap(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager
    demarches_description = [
        humanize_demarche_names(demarche) for demarche in connection.demarches
    ]
    duree = connection.get_duree_keyword_display()
    is_remote = connection.mandat_is_remote

    if request.method == "GET":
        form = RecapMandatForm(aidant)
        return render(
            request,
            "aidants_connect_web/new_mandat/new_mandat_recap.html",
            {
                "aidant": aidant,
                "usager": usager,
                "demarches": demarches_description,
                "duree": duree,
                "is_remote": is_remote,
                "form": form,
            },
        )

    else:
        form = RecapMandatForm(aidant=aidant, data=request.POST)

        if form.is_valid():
            now = timezone.now()
            expiration_date = {
                "SHORT": now + timedelta(days=1),
                "LONG": now + timedelta(days=365),
                "EUS_03_20": settings.ETAT_URGENCE_2020_LAST_DAY,
            }
            mandat_expiration_date = expiration_date.get(connection.duree_keyword)
            days_before_expiration_date = {
                "SHORT": 1,
                "LONG": 365,
                "EUS_03_20": 1 + (settings.ETAT_URGENCE_2020_LAST_DAY - now).days,
            }
            mandat_duree = days_before_expiration_date.get(connection.duree_keyword)

            try:
                connection.demarches.sort()

                # Create a mandat
                mandat = Mandat.objects.create(
                    organisation=aidant.organisation,
                    usager=usager,
                    duree_keyword=connection.duree_keyword,
                    expiration_date=mandat_expiration_date,
                    is_remote=connection.mandat_is_remote,
                )

                # Add a Journal 'create_attestation' action
                Journal.log_attestation_creation(
                    aidant=aidant,
                    usager=usager,
                    demarches=connection.demarches,
                    duree=mandat_duree,
                    is_remote_mandat=connection.mandat_is_remote,
                    access_token=connection.access_token,
                    attestation_hash=generate_attestation_hash(
                        aidant, usager, connection.demarches, mandat_expiration_date
                    ),
                    mandat=mandat,
                )

                # This loop creates one `autorisation` object per `démarche` in the form
                for demarche in connection.demarches:
                    # Revoke existing demarche autorisation(s)
                    similar_active_autorisations = Autorisation.objects.active().filter(
                        mandat__organisation=aidant.organisation,
                        mandat__usager=usager,
                        demarche=demarche,
                    )
                    for similar_active_autorisation in similar_active_autorisations:
                        similar_active_autorisation.revoke(
                            aidant=aidant, revocation_date=now
                        )

                    # Create new demarche autorisation
                    autorisation = Autorisation.objects.create(
                        mandat=mandat,
                        demarche=demarche,
                        last_renewal_token=connection.access_token,
                    )
                    Journal.log_autorisation_creation(autorisation, aidant)

            except AttributeError as error:
                log.error("Error happened in Recap")
                log.error(error)
                django_messages.error(request, f"Error with Usager attribute : {error}")
                return redirect("espace_aidant_home")

            except IntegrityError as error:
                log.error("Error happened in Recap")
                log.error(error)
                django_messages.error(request, f"No Usager was given : {error}")
                return redirect("espace_aidant_home")

            return redirect("new_mandat_success")

        else:
            return render(
                request,
                "aidants_connect_web/new_mandat/new_mandat_recap.html",
                {
                    "aidant": aidant,
                    "usager": usager,
                    "demarche": demarches_description,
                    "duree": duree,
                    "form": form,
                },
            )


@login_required
@user_is_aidant
@activity_required
def new_mandat_success(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager

    return render(
        request,
        "aidants_connect_web/new_mandat/new_mandat_success.html",
        {"aidant": aidant, "usager": usager},
    )


@login_required
@user_is_aidant
@activity_required
def attestation_projet(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    aidant = request.user
    usager = connection.usager
    demarches = connection.demarches

    # Django magic :
    # https://docs.djangoproject.com/en/3.0/ref/models/instances/#django.db.models.Model.get_FOO_display
    duree = connection.get_duree_keyword_display()

    return render(
        request,
        "aidants_connect_web/attestation.html",
        {
            "usager": usager,
            "aidant": aidant,
            "date": formats.date_format(date.today(), "l j F Y"),
            "demarches": [humanize_demarche_names(demarche) for demarche in demarches],
            "duree": duree,
            "current_mandat_template": settings.MANDAT_TEMPLATE_PATH,
        },
    )


@login_required
@user_is_aidant
@activity_required
def attestation_final(request):
    connection = Connection.objects.get(pk=request.session["connection"])
    # noinspection PyTypeChecker
    aidant: Aidant = request.user
    usager = connection.usager
    demarches = connection.demarches

    # Django magic :
    # https://docs.djangoproject.com/en/3.0/ref/models/instances/#django.db.models.Model.get_FOO_display
    duree = connection.get_duree_keyword_display()

    return __attestation_visualisation(
        request,
        settings.MANDAT_TEMPLATE_PATH,
        usager,
        aidant,
        date.today(),
        demarches,
        duree,
    )


@login_required
@user_is_aidant
@activity_required
def attestation_visualisation(request, mandat_id):
    # noinspection PyTypeChecker
    aidant: Aidant = request.user
    mandat_query_set = Mandat.objects.filter(pk=mandat_id)
    if mandat_query_set.count() != 1:
        mailto_body = render_to_string(
            "aidants_connect_web/mandate_visualisation_errors/not_found_email_body.txt",
            request=request,
            context={"mandat_id": mandat_id},
        )

        return render(
            request,
            "aidants_connect_web/mandate_visualisation_errors/error_page.html",
            {
                "mandat_id": mandat_id,
                "support_email": settings.SUPPORT_EMAIL,
                "mailto": generate_mailto_link(
                    settings.SUPPORT_EMAIL,
                    f"Problème en essayant de visualiser le mandat n°{mandat_id}",
                    mailto_body,
                ),
            },
        )

    mandat: Mandat = mandat_query_set.first()
    template = mandat.get_mandate_template_path()

    if template is not None:
        # At this point, the generated QR code on the mandate comes from an independant
        # HTTP request. Normally, what we should do is to modifiy how this HTTP request
        # is done so that the mandate ID is passed during the request. But the mandate
        # template can't be modified anymore because that would change their hash and
        # defeat the algorithm that recovers the original mandate template from the
        # journal entries. The only found solution, which is not nice, is to retain the
        # mandate ID as a session state. Please forgive us for what we did...
        request.session["qr_code_mandat_id"] = mandat_id
        modified = False
    else:
        template = settings.MANDAT_TEMPLATE_PATH
        modified = True

    procedures = [it.demarche for it in mandat.autorisations.all()]
    return __attestation_visualisation(
        request,
        template,
        mandat.usager,
        aidant,
        mandat.creation_date.date(),
        procedures,
        mandat.get_duree_keyword_display(),
        modified=modified,
    )


def __attestation_visualisation(
    request,
    template: str,
    usager: Usager,
    aidant: Aidant,
    attestation_date: date,
    demarches: Collection[str],
    duree: str,
    modified: bool = False,
):
    return render(
        request,
        "aidants_connect_web/attestation.html",
        {
            "usager": usager,
            "aidant": aidant,
            "date": formats.date_format(attestation_date, "l j F Y"),
            "demarches": [humanize_demarche_names(demarche) for demarche in demarches],
            "duree": duree,
            "current_mandat_template": template,
            "final": True,
            "modified": modified,
        },
    )


def get_attestation_hash(mandat_id):
    try:
        mandat = Mandat.objects.get(pk=mandat_id)
        journal = Journal.find_attestation_creation_entries(mandat)
        # If the journal count is 1, let's use this, otherwise, we don't consider
        # the results to be sufficiently specific to display a hash
        if journal.count() == 1:
            return journal.first().attestation_hash
    except Exception:
        return None


@login_required
@user_is_aidant
@activity_required
def attestation_qrcode(request):
    attestation_hash = None
    connection = request.session.get("connection", None)
    mandat_id = request.session.pop("qr_code_mandat_id", None)

    if mandat_id is not None:
        attestation_hash = get_attestation_hash(mandat_id)

    elif connection is not None:
        connection = Connection.objects.get(pk=connection)
        aidant = request.user

        journal_create_attestation = aidant.get_journal_create_attestation(
            connection.access_token
        )
        if journal_create_attestation is not None:
            attestation_hash = journal_create_attestation.attestation_hash

    if attestation_hash is not None:
        qrcode_png = generate_qrcode_png(attestation_hash)
    else:
        with open(finders.find("images/empty_qr_code.png"), "rb") as f:
            qrcode_png = f.read()

    return HttpResponse(qrcode_png, "image/png")
