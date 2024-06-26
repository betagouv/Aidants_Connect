# Generated by Django 4.2.10 on 2024-03-20 09:05

from django.db import migrations

import pgtrigger.compiler
import pgtrigger.migrations


class Migration(migrations.Migration):

    dependencies = [
        ('aidants_connect_common', '0005_formation_formationattendant_formationtype_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='formationattendant',
            options={'verbose_name': 'Formation\xa0: inscrit', 'verbose_name_plural': 'Formation\xa0: inscrits'},
        ),
        migrations.AlterModelOptions(
            name='formationtype',
            options={'verbose_name': 'Formation\xa0: types', 'verbose_name_plural': 'Formation\xa0: types'},
        ),
        pgtrigger.migrations.RemoveTrigger(
            model_name='formationattendant',
            name='check_attendants_count',
        ),
        pgtrigger.migrations.AddTrigger(
            model_name='formationattendant',
            trigger=pgtrigger.compiler.Trigger(name='check_attendants_count', sql=pgtrigger.compiler.UpsertTriggerSql(declare='DECLARE attendants_count INTEGER; max_attendants_count INTEGER;', func="-- prevent concurrent inserts from multiple transactions\nLOCK TABLE aidants_connect_common_formationattendant IN EXCLUSIVE MODE;\n\nSELECT INTO attendants_count COUNT(*)\nFROM aidants_connect_common_formationattendant\nWHERE formation_id = NEW.formation_id;\n\nSELECT max_attendants INTO max_attendants_count\nFROM aidants_connect_common_formation\nWHERE id = NEW.formation_id;\n\nIF attendants_count >= max_attendants_count THEN\n    RAISE EXCEPTION 'Formation is already full.' USING ERRCODE = 'check_violation';\nEND IF;\n\nRETURN NEW;", hash='bb365cff87165c52b4d6ba5683ab07d79ec01bbf', operation='INSERT OR UPDATE', pgid='pgtrigger_check_attendants_count_de7ba', table='aidants_connect_common_formationattendant', when='BEFORE')),
        ),
    ]
