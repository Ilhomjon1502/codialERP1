import datetime

import pytest
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import Role
from apps.core.permissions import can, check_edit_window
from apps.core.roles import DEFAULT_PERMISSIONS, edit_days
from apps.references.models import LessonTime, Room

pytestmark = pytest.mark.django_db


def test_default_matrix_seeded_from_prototype():
    assert DEFAULT_PERMISSIONS["ADMIN"]["settings"] == "vaed"
    assert DEFAULT_PERMISSIONS["FILIAL_MENEJERI"]["settings"] == "vae"
    assert DEFAULT_PERMISSIONS["USTOZ"]["settings"] == ""
    assert DEFAULT_PERMISSIONS["BOSH_MENEJER"]["ai"] == "v"
    r = Role.objects.get(code="ADMINISTRATOR")
    assert dict(r.permissions.values_list("section", "ops"))["leads"] == "vaed"
    assert set(Role.objects.get(code="FILIAL_MENEJERI").can_assign.values_list("code", flat=True)) >= {"USTOZ", "HISOBCHI"}
    assert "ADMIN" not in set(Role.objects.get(code="BOSH_MENEJER").can_assign.values_list("code", flat=True))


@pytest.mark.parametrize(
    "role, get, post",
    [("ADMIN", 200, 201), ("FILIAL_MENEJERI", 200, 201), ("ADMINISTRATOR", 200, 403), ("HISOBCHI", 200, 403), ("USTOZ", 403, 403)],
)
def test_section_permission_by_method(api, make_user, role, get, post):
    c = api(make_user(role))
    assert c.get("/api/v1/lead-sources/").status_code == get
    r = c.post("/api/v1/lead-sources/", {"name": f"Manba {role}"}, format="json")
    assert r.status_code == post
    if post == 403:
        assert r.json()["detail"] == "Sizning rolingizda bu amalga ruxsat yo'q"


def test_delete_requires_d(api, make_user):
    src = api(make_user("ADMIN")).post("/api/v1/lead-sources/", {"name": "Sayt"}, format="json").json()
    assert api(make_user("FILIAL_MENEJERI")).delete(f"/api/v1/lead-sources/{src['id']}/").status_code == 403
    assert api(make_user("BOSH_MENEJER")).delete(f"/api/v1/lead-sources/{src['id']}/").status_code == 204


def test_branch_scoping(api, make_user, branch, other_branch):
    Room.objects.create(branch=branch, name="1-xona", capacity=10)
    Room.objects.create(branch=other_branch, name="A-xona", capacity=8)
    fm = make_user("FILIAL_MENEJERI", branches=[branch])
    names = [r["name"] for r in api(fm).get("/api/v1/rooms/").json()]
    assert names == ["1-xona"]
    assert len(api(make_user("BOSH_MENEJER")).get("/api/v1/rooms/").json()) == 2
    r = api(fm).post("/api/v1/rooms/", {"branch": str(other_branch.pk), "name": "B", "capacity": 5}, format="json")
    assert r.status_code == 400 and r.json()["branch"] == ["Bu filial sizning doirangizda emas"]


def test_branch_cannot_change_after_create(api, make_user, branch, other_branch):
    t = LessonTime.objects.create(branch=branch, start_time="08:00", end_time="10:00")
    r = api(make_user("ADMIN")).patch(f"/api/v1/lesson-times/{t.pk}/", {"branch": str(other_branch.pk)}, format="json")
    assert r.status_code == 400 and "o'zgartirib bo'lmaydi" in r.json()["branch"][0]


def test_branches_write_only_top(api, make_user):
    assert api(make_user("FILIAL_MENEJERI")).post("/api/v1/branches/", {"name": "Yangi"}, format="json").status_code == 403
    assert api(make_user("BOSH_MENEJER")).post("/api/v1/branches/", {"name": "Yangi"}, format="json").status_code == 201


def test_edit_days_rules():
    assert edit_days("ADMIN", "payments") is None
    assert edit_days("BOSH_MENEJER", "contracts") is None
    assert edit_days("FILIAL_MENEJERI", "leads") == 15
    assert edit_days("ADMINISTRATOR", "contracts") == 7
    assert edit_days("ADMINISTRATOR", "payments") == 0
    assert edit_days("HISOBCHI", "expenses") == 0
    assert edit_days("USTOZ", "attendance") == 0


def test_check_edit_window(make_user, monkeypatch):
    import apps.core.permissions as p

    monkeypatch.setattr(p, "today", lambda: datetime.date(2026, 10, 20))
    adm = make_user("ADMINISTRATOR")
    check_edit_window(adm, "leads", datetime.date(2026, 10, 13))  # 7 kun — mumkin
    with pytest.raises(PermissionDenied, match="oxirgi 7 kun"):
        check_edit_window(adm, "leads", datetime.date(2026, 10, 12))
    with pytest.raises(PermissionDenied, match="ruxsat yo'q"):
        check_edit_window(adm, "payments", datetime.date(2026, 10, 20))  # bo'limga ruxsat yo'q
    bm = make_user("BOSH_MENEJER")
    check_edit_window(bm, "payments", datetime.date(2020, 1, 1))
    assert can(bm, "payments", "p")
