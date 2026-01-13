# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Profile
from django.utils.text import slugify
from django.db.models.signals import pre_save
import shortuuid

@receiver(pre_save, sender=Profile)
def generate_slug(sender, instance, **kwargs):
    if not instance.slug:
        base = slugify(instance.full_name or instance.user.username)
        slug = base
        i = 1
        while Profile.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
            slug = f"{base}-{i}"
            i += 1
        instance.slug = slug

User = get_user_model()

@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        profile = Profile.objects.create(user=instance)
        profile.delete_code = "D" + shortuuid.uuid()[:6].upper()
        profile.save()

@receiver(post_save, sender=User)
def auto_fill_profile(sender, instance, created, **kwargs):
    if hasattr(instance, 'profile') and not instance.profile.full_name:
        instance.profile.full_name = instance.get_full_name() or instance.username
        instance.profile.save()





