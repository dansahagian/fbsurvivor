# Generated by Django 5.1.1 on 2024-09-25 20:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0045_season_description"),
    ]

    operations = [
        migrations.AddField(
            model_name="season",
            name="is_live",
            field=models.BooleanField(default=False),
        ),
    ]
