from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    is_mall_owner = models.BooleanField(default=False)
    is_admin = models.BooleanField(default=False)
    is_user = models.BooleanField(default=True)  # Optional if you want to track user role

    def __str__(self):
        return self.username

    def save(self, *args, **kwargs):
        """Ensure Django admin access flag aligns with app roles.

        Any mall owner or admin (or superuser) should be allowed to access
        the Django admin site, so we set is_staff accordingly.
        Regular users should not have staff access.
        """
        self.is_staff = bool(self.is_superuser or self.is_admin or self.is_mall_owner)
        super().save(*args, **kwargs)