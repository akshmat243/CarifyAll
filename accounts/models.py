from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils.text import slugify
import uuid
# from django.contrib.auth.models import AbstractUser
# from django.db import models

# class User(AbstractUser):
#     full_name = models.CharField(max_length=255, blank=True)
#     role = models.CharField(max_length=50, blank=True)
#     slug = models.SlugField(unique=True, blank=True, null=True)

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('is_email_verified', True)
        extra_fields.setdefault('is_phone_verified', True)

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=15, unique=True, blank=True, null=True) 
    full_name = models.CharField(max_length=100, blank=True)
    role = models.ForeignKey('MBP.Role', null=True, blank=True, on_delete=models.CASCADE,related_name="accounts_users")
    slug = models.SlugField(unique=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='created_users')
    
    is_email_verified = models.BooleanField(default=False)
    is_phone_verified = models.BooleanField(default=True)
    
    force_password_change = models.BooleanField(
        default=False,
        help_text="User must change password on first login or after admin reset."
    )

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['phone']

    def __str__(self):
        return self.email
    
    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.full_name or self.email.split('@')[0])
            slug = base_slug
            count = 1
            while User.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            self.slug = slug
            
        # self.is_active = self.is_email_verified and self.is_phone_verified
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

# class Profile(models.Model):
#     user = models.OneToOneField(
#         "accounts.User",
#         on_delete=models.CASCADE
#     )
#     # role = models.ForeignKey(
#     #     "MBP.Role",
#     #     on_delete=models.CASCADE
#     # )



class UserModule(models.Model):
    MODULE_CHOICES = [
        ("hotel", "Hotel"),
        ("restaurant", "Restaurant"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="modules")
    module = models.CharField(max_length=20, choices=MODULE_CHOICES)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("user", "module")
