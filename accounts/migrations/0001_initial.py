from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="PasskeyCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("credential_id", models.CharField(max_length=255, unique=True)),
                ("public_key", models.TextField()),
                ("sign_count", models.PositiveIntegerField(default=0)),
                (
                    "device_label",
                    models.CharField(
                        blank=True,
                        help_text="e.g. 'Tushar's iPhone' — just for your own reference.",
                        max_length=100,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_used_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
