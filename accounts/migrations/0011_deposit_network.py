from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_userprofile_has_withdrawn"),
    ]

    operations = [
        migrations.AddField(
            model_name="deposit",
            name="network",
            field=models.CharField(
                choices=[
                    ("tron", "TRON (TRC20)"),
                    ("ton", "TON"),
                    ("polygon", "Polygon (ERC20)"),
                    ("bep", "BNB Chain (BEP20)"),
                ],
                default="tron",
                max_length=20,
            ),
        ),
    ]
