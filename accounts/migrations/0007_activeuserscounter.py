from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0006_alter_notification_target_all_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="ActiveUsersCounter",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("value", models.PositiveIntegerField(default=200)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
