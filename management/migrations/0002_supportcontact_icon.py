from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("management", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="supportcontact",
            name="icon",
            field=models.ImageField(blank=True, null=True, upload_to="support_icons/"),
        ),
    ]
