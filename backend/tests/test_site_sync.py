import datetime
import hashlib
import hmac

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.crm import inbox, site_sync
from apps.crm.models import InboxLead

pytestmark = pytest.mark.django_db


@pytest.fixture
def sent(monkeypatch):
    out = []
    monkeypatch.setattr("apps.crm.site_sync.transaction.on_commit", lambda f: f())
    monkeypatch.setattr(site_sync, "_send", out.append)
    return out


def test_site_ingest_stores_external_id_and_is_idempotent(api, branch):
    with override_settings(INBOX_SITE_KEY="k" * 20):
        c = api()
        body = {"id": "site:7", "name": "Ali", "phone": "+998 (93) 321-19-90", "course": "Vibe Coding", "message": ""}
        assert c.post("/api/v1/inbox/site/", body, format="json", HTTP_X_INBOX_KEY="k" * 20).status_code == 201
        assert c.post("/api/v1/inbox/site/", body, format="json", HTTP_X_INBOX_KEY="k" * 20).status_code == 200
        assert c.post("/api/v1/inbox/site/", body, format="json", HTTP_X_INBOX_KEY="x" * 20).status_code == 403
    assert InboxLead.objects.get().external_id == "site:7"


def test_site_ingest_ignores_foreign_external_id(api, branch):
    with override_settings(INBOX_SITE_KEY="k" * 20):
        api().post("/api/v1/inbox/site/", {"id": "../../x", "phone": "933211990"}, format="json", HTTP_X_INBOX_KEY="k" * 20)
    assert InboxLead.objects.get().external_id is None


def test_talk_link_reopen_notify_site(branch, make_user, sent):
    user = make_user("BOSH_MENEJER")
    item, _ = inbox.add("Sayt", phone="933211990", name="Ali", external_id="site:7")
    inbox.talk(user, item, "Telefon qilindi, juma kuni keladi", callback_at=timezone.now() + datetime.timedelta(days=1), outcome="hesitate")
    assert sent[-1] == {"id": "site:7", "status": "callback", "note": "Telefon qilindi, juma kuni keladi"}
    inbox.talk(user, item, "Qiziqmadi", close=True, outcome="bad")
    assert sent[-1]["status"] == "rejected"
    inbox.reopen(user, item)
    assert sent[-1] == {"id": "site:7", "status": "new", "note": ""}


def test_other_sources_are_not_sent(branch, make_user, sent):
    user = make_user("BOSH_MENEJER")
    ig, _ = inbox.add("Instagram", phone="933211991", external_id="l:5")
    site_no_id, _ = inbox.add("Sayt", phone="933211992")
    inbox.talk(user, ig, "x", close=True, outcome="bad")
    inbox.talk(user, site_no_id, "x", close=True, outcome="bad")
    assert sent == []


def test_signature_matches_site_algorithm():
    body = b'{"id":"site:7"}'
    expected = hmac.new(b"secret", b"1700000000." + body, hashlib.sha256).hexdigest()
    assert site_sync.sign("secret", "1700000000", body) == expected
