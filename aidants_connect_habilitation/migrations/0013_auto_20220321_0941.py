from django.db import migrations, models

import aidants_connect_habilitation.models


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_habilitation', '0012_auto_20220314_1530'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='organisationrequest',
            name='cgu_checked',
        ),
        migrations.RemoveConstraint(
            model_name='organisationrequest',
            name='dpo_checked',
        ),
        migrations.RemoveConstraint(
            model_name='organisationrequest',
            name='professionals_only_checked',
        ),
        migrations.RemoveConstraint(
            model_name='organisationrequest',
            name='without_elected_checked',
        ),
        migrations.RemoveConstraint(
            model_name='organisationrequest',
            name='manager_set',
        ),
        migrations.RemoveConstraint(
            model_name='organisationrequest',
            name='data_privacy_officer_set',
        ),
        migrations.RemoveField(
            model_name='organisationrequest',
            name='draft_id',
        ),
        migrations.AddField(
            model_name='organisationrequest',
            name='uuid',
            field=models.UUIDField(default=aidants_connect_habilitation.models._new_uuid, unique=True, verbose_name='Identifiant de brouillon'),
        ),
        migrations.AddConstraint(
            model_name='organisationrequest',
            constraint=models.CheckConstraint(check=models.Q(('status', 'NEW'), models.Q(models.Q(('status', 'NEW'), _negated=True), ('cgu', True)), _connector='OR'), name='cgu_checked'),
        ),
        migrations.AddConstraint(
            model_name='organisationrequest',
            constraint=models.CheckConstraint(check=models.Q(('status', 'NEW'), models.Q(models.Q(('status', 'NEW'), _negated=True), ('dpo', True)), _connector='OR'), name='dpo_checked'),
        ),
        migrations.AddConstraint(
            model_name='organisationrequest',
            constraint=models.CheckConstraint(check=models.Q(('status', 'NEW'), models.Q(models.Q(('status', 'NEW'), _negated=True), ('professionals_only', True)), _connector='OR'), name='professionals_only_checked'),
        ),
        migrations.AddConstraint(
            model_name='organisationrequest',
            constraint=models.CheckConstraint(check=models.Q(('status', 'NEW'), models.Q(models.Q(('status', 'NEW'), _negated=True), ('without_elected', True)), _connector='OR'), name='without_elected_checked'),
        ),
        migrations.AddConstraint(
            model_name='organisationrequest',
            constraint=models.CheckConstraint(check=models.Q(('status', 'NEW'), models.Q(models.Q(('status', 'NEW'), _negated=True), ('manager__isnull', False)), _connector='OR'), name='manager_set'),
        ),
        migrations.AddConstraint(
            model_name='organisationrequest',
            constraint=models.CheckConstraint(check=models.Q(('status', 'NEW'), models.Q(models.Q(('status', 'NEW'), _negated=True), ('data_privacy_officer__isnull', False)), _connector='OR'), name='data_privacy_officer_set'),
        ),
    ]
