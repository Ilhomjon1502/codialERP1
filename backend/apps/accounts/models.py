import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

from apps.core.models import BaseModel
from apps.core.roles import RoleCode

TEAMS = ["Qabul", "Marketing", "Moliya", "HR", "Ta'lim", "Boshqa", "Qurilish va ta'mirlash", "IT", "Ta'minot"]


class Role(BaseModel):
    code = models.CharField(max_length=32, unique=True, choices=RoleCode.choices)
    name = models.CharField("Nomi", max_length=64)
    sort = models.PositiveSmallIntegerField(default=0)
    can_assign = models.ManyToManyField("self", symmetrical=False, blank=True, related_name="+", verbose_name="Tayinlay oladigan rollari (RolePower)")

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Rollar"
        ordering = ["sort"]

    def __str__(self):
        return self.name


class RolePermission(models.Model):
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name="permissions")
    section = models.CharField("Bo'lim", max_length=32)
    ops = models.CharField("Ruxsatlar (vaedp)", max_length=5, blank=True)

    class Meta:
        verbose_name = "Rol ruxsati"
        verbose_name_plural = "Rol ruxsatlari"
        constraints = [models.UniqueConstraint(fields=["role", "section"], name="uniq_role_section")]

    def __str__(self):
        return f"{self.role} · {self.section}: {self.ops or '—'}"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)

    def _create(self, email, password, **extra):
        user = self.model(email=self.normalize_email(email) if email else None, **extra)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save(using=self._db)
        return user

    def create_user(self, email=None, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(is_staff=True, is_superuser=True)
        extra.setdefault("role", Role.objects.filter(code=RoleCode.ADMIN).first())
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    class Employment(models.TextChoices):
        ACTIVE = "Faol", "Faol"
        LEFT = "Ishdan ketgan", "Ishdan ketgan"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField("Pochta (login)", unique=True, null=True, blank=True)
    full_name = models.CharField("To'liq ism", max_length=150, unique=True)
    phone = models.CharField("Telefon", max_length=9, blank=True)
    role = models.ForeignKey(Role, null=True, on_delete=models.PROTECT, related_name="users", verbose_name="Lavozim")
    branches = models.ManyToManyField("references.Branch", blank=True, related_name="users", verbose_name="Filiallar")
    teams = models.JSONField("Bo'limlar", default=list, blank=True)
    employment_status = models.CharField("Holat", max_length=16, choices=Employment.choices, default=Employment.ACTIVE, db_index=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField("Django admin", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    legacy_id = models.CharField(max_length=64, null=True, blank=True, db_index=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "Xodim"
        verbose_name_plural = "Xodimlar"
        ordering = ["full_name"]

    def save(self, *args, **kwargs):
        # Ishdan ketgan xodim tizimga kira olmaydi, lekin tarixi saqlanadi
        self.is_active = self.employment_status == self.Employment.ACTIVE
        if self.email == "":
            self.email = None
        super().save(*args, **kwargs)

    def __str__(self):
        return self.full_name
