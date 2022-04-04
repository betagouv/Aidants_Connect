from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_habilitation', '0014_auto_20220324_1713'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='organisationrequest',
            name='data_privacy_officer_set',
        ),
        migrations.RemoveField(
            model_name='organisationrequest',
            name='data_privacy_officer',
        ),
        migrations.DeleteModel(
            name='DataPrivacyOfficer',
        ),
    ]
