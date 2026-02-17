from django.db import models

class SupportContact(models.Model):
    PLATFORM_WHATSAPP = "whatsapp"
    PLATFORM_TELEGRAM = "telegram"
    PLATFORM_WEBSITE = "website"
    PLATFORM_EMAIL = "email"
    PLATFORM_PHONE = "phone"
    PLATFORM_OTHER = "other"

    PLATFORM_CHOICES = (
        (PLATFORM_WHATSAPP, "WhatsApp"),
        (PLATFORM_TELEGRAM, "Telegram"),
        (PLATFORM_WEBSITE, "Website"),
        (PLATFORM_EMAIL, "Email"),
        (PLATFORM_PHONE, "Phone"),
        (PLATFORM_OTHER, "Other"),
    )

    platform = models.CharField(max_length=20, choices=PLATFORM_CHOICES, default=PLATFORM_WHATSAPP)
    title = models.CharField(max_length=100)
    url = models.CharField(max_length=500)
    icon = models.ImageField(upload_to="support_icons/", null=True, blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("order", "id")

    def __str__(self):
        return f"{self.title} ({self.get_platform_display()})"
