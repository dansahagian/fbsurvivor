# Generated by Django 5.1.1 on 2024-09-21 20:52

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0043_delete_cachedboard"),
    ]

    operations = [
        migrations.CreateModel(
            name="EmailLogRecord",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("subject", models.CharField(max_length=128)),
                ("email", models.CharField(max_length=128)),
            ],
        ),
    ]