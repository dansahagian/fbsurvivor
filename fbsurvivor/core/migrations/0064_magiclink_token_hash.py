import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import fbsurvivor.core.models


class Migration(migrations.Migration):
    """Store only a hash of the magic-link token instead of the raw token.

    Outstanding links are short-lived (15 minutes) and single-use, so the old
    rows are disposable; the model is dropped and recreated with the hashed
    primary key.
    """

    dependencies = [
        ("core", "0063_alter_payout_options_lock_unique_lock_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.DeleteModel(
            name="MagicLink",
        ),
        migrations.CreateModel(
            name="MagicLink",
            fields=[
                (
                    "token_hash",
                    models.CharField(
                        max_length=64,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "expires_at",
                    models.DateTimeField(default=fbsurvivor.core.models.calculate_expires_at),
                ),
                ("logged_in_at", models.DateTimeField(null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="magic_links",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
        ),
    ]
