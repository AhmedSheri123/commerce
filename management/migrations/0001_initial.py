from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SupportContact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "platform",
                    models.CharField(
                        choices=[
                            ("whatsapp", "WhatsApp"),
                            ("telegram", "Telegram"),
                            ("website", "Website"),
                            ("email", "Email"),
                            ("phone", "Phone"),
                            ("other", "Other"),
                        ],
                        default="whatsapp",
                        max_length=20,
                    ),
                ),
                ("title", models.CharField(max_length=100)),
                ("url", models.CharField(max_length=500)),
                ("is_active", models.BooleanField(default=True)),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("order", "id"),
            },
        ),
    ]
