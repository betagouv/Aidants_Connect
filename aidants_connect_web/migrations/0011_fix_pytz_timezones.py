from django.db import migrations


# TODO: Eliniminate this migration in a future squash
class Migration(migrations.Migration):
    dependencies = [
        ("aidants_connect_web", "0010_auto_20220825_1121"),
    ]

    operations = [
        migrations.RunPython(migrations.RunPython.noop)
    ]
