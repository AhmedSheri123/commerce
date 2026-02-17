from django.contrib import admin
from .models import UserProfile, Notification, NotificationRead
# Register your models here.

admin.site.register(UserProfile)
admin.site.register(Notification)
admin.site.register(NotificationRead)
