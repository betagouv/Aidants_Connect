# Generated by Django 4.2.15 on 2024-09-26 13:42

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_habilitation', '0032_organisationrequest_not_free_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='organisationrequest',
            name='status',
            field=models.CharField(choices=[('NEW', 'Brouillon'), ('AC_VALIDATION_PROCESSING', 'En attente de validation d’éligibilité avant inscription en formation des aidants'), ('VALIDATED', 'Éligibilité validée'), ('REFUSED', 'Éligibilité Refusée'), ('CLOSED', 'Clôturée'), ('CHANGES_REQUIRED', 'Demande de modifications par l’équipe Aidants Connect'), ('CHANGES_PROPOSED', 'Modifications proposées par Aidants Connect')], default='NEW', max_length=150, verbose_name='État'),
        ),
    ]
