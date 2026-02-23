from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from accounts.models import UserProfile
from wallet.services import ensure_user_wallets


@receiver(post_save, sender=User)
def ensure_wallets_for_new_user(sender, instance, created, **kwargs):
    if created:
        ensure_user_wallets(instance)


@receiver(post_save, sender=UserProfile)
def ensure_wallets_for_profile(sender, instance, created, **kwargs):
    if created:
        ensure_user_wallets(instance.user)
