def __2023_08_24_suppress_aidant_duplicates():
    from django.db.models import Count, Q
    from django.db.models.functions import Lower

    from aidants_connect_web.models import Aidant, Journal

    duplicates = (
        Aidant.objects.annotate(lowercase_username=Lower("username"))
        .values("lowercase_username")
        .annotate(dups=Count("*"))
        .filter(dups__gt=1)
        .values_list("lowercase_username", flat=True)
    )

    for duplicate in duplicates:
        try:
            target = Aidant.objects.get(username=duplicate)
        except Aidant.DoesNotExist:
            try:
                Aidant.objects.filter(
                    username__iexact=duplicate, carte_totp__isnull=False
                ).first()
            except Aidant.DoesNotExist:
                print(duplicate)
                continue

        others = (
            Aidant.objects.filter(~Q(pk=target.pk))
            .annotate(lowercase_username=Lower("username"))
            .filter(lowercase_username=duplicate)
            .all()
        )

        Journal.objects.filter(
            aidant__in=others, organisation=target.organisation
        ).update(aidant=target)

        others.delete()
