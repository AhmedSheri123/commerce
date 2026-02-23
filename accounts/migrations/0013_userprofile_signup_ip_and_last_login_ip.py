from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0012_alter_deposit_status_alter_transaction_status_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="signup_ip",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="last_login_ip",
            field=models.GenericIPAddressField(blank=True, null=True),
        ),
    ]
