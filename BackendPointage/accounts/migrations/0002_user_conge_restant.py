# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="conge_restant",
            field=models.PositiveIntegerField(default=24),
        ),
    ]
