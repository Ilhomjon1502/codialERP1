import re

import pytest
from django.core import mail

from apps.accounts import services
from apps.core.models import AuditLog

from .conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_login_me_logout(api, make_user):
    u = make_user("FILIAL_MENEJERI", email="Malika@Codial.test")
    c = api()
    r = c.post("/api/v1/auth/login/", {"email": "malika@codial.test", "password": PASSWORD}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["role"] == "FILIAL_MENEJERI"
    assert "v" in r.json()["perms"]["settings"]
    assert c.get("/api/v1/auth/me/").json()["id"] == str(u.pk)
    assert AuditLog.objects.filter(action="login", object_id=str(u.pk)).exists()
    assert c.post("/api/v1/auth/logout/").status_code == 200
    assert c.get("/api/v1/auth/me/").status_code == 401


def test_wrong_password_and_unauthenticated(api, make_user):
    make_user(email="a@codial.test")
    r = api().post("/api/v1/auth/login/", {"email": "a@codial.test", "password": "xato"}, format="json")
    assert r.status_code == 400
    assert r.json()["detail"] == "Pochta yoki parol noto'g'ri"
    r = api().get("/api/v1/bootstrap/")
    assert r.status_code == 401 and r.json()["code"] == "not_authenticated"


def test_left_employee_cannot_login(api, make_user):
    u = make_user(email="ketgan@codial.test")
    u.employment_status = "Ishdan ketgan"
    u.save()
    assert not u.is_active
    r = api().post("/api/v1/auth/login/", {"email": "ketgan@codial.test", "password": PASSWORD}, format="json")
    assert r.status_code == 400


def test_password_link_and_set(api, make_user):
    u = make_user(email="yangi@codial.test", password=None)
    assert not u.has_usable_password()
    services.send_password_link(u)
    assert len(mail.outbox) == 1
    link = re.search(r"https://\S+", mail.outbox[0].body).group(0)
    assert link.startswith("https://test.example.uz/#/set-password?uid=")
    uid, token = re.search(r"uid=([^&]+)&token=(\S+)", link).groups()
    c = api()
    weak = c.post("/api/v1/auth/password/set/", {"uid": uid, "token": token, "password": "123"}, format="json")
    assert weak.status_code == 400 and "password" in weak.json()
    ok = c.post("/api/v1/auth/password/set/", {"uid": uid, "token": token, "password": "1234"}, format="json")  # oddiy parol ham mumkin
    assert ok.status_code == 200
    # Havola bir marta ishlaydi
    again = c.post("/api/v1/auth/password/set/", {"uid": uid, "token": token, "password": "Boshqa-Parol-88"}, format="json")
    assert again.status_code == 400
    assert c.post("/api/v1/auth/login/", {"email": "yangi@codial.test", "password": "1234"}, format="json").status_code == 200


def test_password_reset_does_not_reveal_email(api, make_user):
    make_user(email="bor@codial.test")
    c = api()
    r1 = c.post("/api/v1/auth/password/reset/", {"email": "bor@codial.test"}, format="json")
    r2 = c.post("/api/v1/auth/password/reset/", {"email": "yoq@codial.test"}, format="json")
    assert r1.status_code == r2.status_code == 200 and r1.json() == r2.json()
    assert len(mail.outbox) == 1


def test_csrf_enforced_for_login_and_writes(make_user):
    from rest_framework.test import APIClient

    make_user("FILIAL_MENEJERI", email="csrf@codial.test")
    c = APIClient(enforce_csrf_checks=True)
    body = {"email": "csrf@codial.test", "password": PASSWORD}
    assert c.post("/api/v1/auth/login/", body, format="json").status_code == 403  # CSRF token yo'q
    c.get("/api/v1/auth/csrf/")
    token = lambda: {"HTTP_X_CSRFTOKEN": c.cookies["csrftoken"].value}  # noqa: E731
    assert c.post("/api/v1/auth/login/", body, format="json", **token()).status_code == 200
    assert c.post("/api/v1/lead-sources/", {"name": "Yangi"}, format="json").status_code == 403
    assert c.post("/api/v1/lead-sources/", {"name": "Yangi"}, format="json", **token()).status_code == 201
