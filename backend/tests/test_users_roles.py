import pytest
from django.core import mail

from apps.accounts.models import Role, RolePermission, User
from apps.core.models import AuditLog

pytestmark = pytest.mark.django_db


def body(branch, **kw):
    return {"full_name": "Yangi Ustoz", "role": "USTOZ", "branches": [str(branch.pk)], "phone": "901234567", "email": "ustoz@codial.test", "teams": ["Ta'lim"], **kw}


def test_create_user_sends_invite(api, make_user, branch, django_capture_on_commit_callbacks):
    fm = make_user("FILIAL_MENEJERI", full_name="Malika Yusupova")
    with django_capture_on_commit_callbacks(execute=True):
        r = api(fm).post("/api/v1/users/", body(branch), format="json")
    assert r.status_code == 201, r.content
    assert r.json()["has_password"] is False and r.json()["status"] == "Faol"
    assert len(mail.outbox) == 1 and "Malika Yusupova sizni Codial ERP" in mail.outbox[0].body
    assert AuditLog.objects.filter(action="create", model="Xodim").exists()


def test_role_power_and_branch_scope(api, make_user, branch, other_branch):
    fm = make_user("FILIAL_MENEJERI")
    c = api(fm)
    r = c.post("/api/v1/users/", body(branch, role="BOSH_MENEJER"), format="json")
    assert r.status_code == 400 and r.json()["role"] == ["Bu rolni tayinlash huquqingiz yo'q"]
    r = c.post("/api/v1/users/", body(branch, branches=[str(other_branch.pk)]), format="json")
    assert r.json()["branches"] == ["Bu filial sizning doirangizda emas"]
    stranger = make_user("USTOZ", branches=[other_branch])
    r = c.patch(f"/api/v1/users/{stranger.pk}/", {"phone": "991112233"}, format="json")
    assert r.status_code == 400 and r.json()["detail"] == ["Bu xodimni tahrirlash huquqingiz yo'q"]


def test_user_validations(api, make_user, branch):
    make_user(full_name="Jasur Aliyev", email="jasur@codial.test")
    c = api(make_user("ADMIN"))
    r = c.post("/api/v1/users/", body(branch, full_name="jasur  aliyev", email="JASUR@codial.test", phone="12"), format="json")
    e = r.json()
    assert e["full_name"] == ["Avval kiritilgan ism! Boshqa nom bering"]
    assert e["email"] == ["Avval kiritilgan pochta!"]
    assert e["phone"] == ["9 sondan iborat bo'lsin. Namuna: 998883322"]
    r = c.post("/api/v1/users/", body(branch, email="", role="USTOZ"), format="json")
    assert r.json()["email"] == ["Majburiy maydon"]
    r = c.post("/api/v1/users/", body(branch, full_name="Farrux Olimov", role="BOSHQA", email="x@codial.test"), format="json")
    assert r.status_code == 201 and r.json()["email"] is None


def test_mark_left_blocks_login(api, make_user):
    u = make_user("USTOZ", email="ketadi@codial.test")
    r = api(make_user("ADMIN")).patch(f"/api/v1/users/{u.pk}/", {"status": "Ishdan ketgan"}, format="json")
    assert r.status_code == 200
    u.refresh_from_db()
    assert not u.is_active
    assert api().post("/api/v1/auth/login/", {"email": "ketadi@codial.test", "password": "x"}, format="json").status_code == 400


def test_users_cannot_be_deleted(api, make_user):
    u = make_user("USTOZ")
    assert api(make_user("ADMIN")).delete(f"/api/v1/users/{u.pk}/").status_code == 405


def test_toggle_permission(api, make_user):
    bm = make_user("BOSH_MENEJER")
    r = api(bm).post("/api/v1/roles/ADMINISTRATOR/toggle/", {"section": "settings", "op": "a"}, format="json")
    assert r.status_code == 200 and r.json()["perms"]["settings"] == "va"
    assert RolePermission.objects.get(role__code="ADMINISTRATOR", section="settings").ops == "va"
    r = api(bm).post("/api/v1/roles/ADMINISTRATOR/toggle/", {"section": "settings", "op": "a"}, format="json")
    assert r.json()["perms"]["settings"] == "v"
    assert api(make_user("FILIAL_MENEJERI")).post("/api/v1/roles/ADMINISTRATOR/toggle/", {"section": "settings", "op": "a"}, format="json").status_code == 403
    r = api(bm).post("/api/v1/roles/ADMIN/toggle/", {"section": "settings", "op": "a"}, format="json")
    assert r.status_code == 403 and r.json()["detail"] == "Admin rolining ruxsatlari o'zgarmaydi"
    assert AuditLog.objects.filter(model="Rol ruxsati").count() == 2


def test_superuser_gets_admin_role():
    u = User.objects.create_superuser(email="root@codial.test", password="x-Long-Pass-1", full_name="Tizim egasi")
    assert u.role == Role.objects.get(code="ADMIN") and u.is_staff
