from django.db import models
import uuid

# Create your models here.
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.contrib.auth.base_user import BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("role", "ADMIN")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):

    ROLE_CHOICES = [
        ("ADMIN", "Admin"),
        ("MANAGER", "Manager"),
        ("EMPLOYE", "Employe"),
    ]

    STATUT_CHOICES = [
        ("ACTIF", "Actif"),
        ("INACTIF", "Inactif"),
    ]
 
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default="ACTIF")

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    #salaire_mensuel = models.FloatField(default=0)
    

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nom", "prenom"]

    def __str__(self):
        return self.email
    
import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class QRDynamic(models.Model):

    TYPE_CHOICES = (
        ("ENTREE", "Entrée"),
        ("SORTIE", "Sortie"),
    )

    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    employe = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE
    )

    type_pointage = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES
    )

    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    is_used = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(seconde=5)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.employe.nom} {self.employe.prenom} - {self.type_pointage}"