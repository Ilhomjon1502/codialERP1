"""Ustozlar ish sifati hisoboti (PDF): davomat qamrovi, ketganlar, baholash, PDF va yuborish."""

import datetime

import pytest
from django.core.management import call_command

from apps.education.models import Contract
from apps.reports import teacher_report
from tests.test_education import TODAY, take, world  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db


def test_coverage_churn_scores_and_pdf(api, world):  # noqa: F811
    w = world
    c0, c1, c2 = w["contracts"]
    assert take(api(w["teacher"]), w, [(c0, "1", ""), (c1, "1", "")]).status_code == 200  # bugun: 3 tadan 2 tasi belgilandi
    Contract.objects.filter(pk=c2.pk).update(end_date=TODAY, stop_reason=Contract.StopReason.QUALITY)

    data = teacher_report.grade(teacher_report.collect(TODAY - datetime.timedelta(days=2), TODAY))
    assert [p["name"] for p in data["teachers"]] == [w["teacher"].full_name]  # yordamchi va guruhsiz ustoz kirmaydi
    p = data["teachers"][0]
    assert p["lessons"] == 3 and len(p["missing"]) == 2 and len(p["partial"]) == 1 and p["unmarked"] == 1
    assert p["timing_n"] == p["same_day"] == 1 and p["by_other"] == 0
    assert p["churn_n"] == 1 and p["presence"] == 1
    assert p["cov"] == pytest.approx(0.5 / 3)
    assert p["parts"]["presence"] == pytest.approx(20 * 0.5 / 3, abs=0.1)  # qamrovga ko'paytirilgan
    assert p["grade"] == "Qoniqarsiz"
    assert any("davomat umuman olinmagan" in x for x in p["bad"]) and any("Dars sifatidan qoniqmadi" in x for x in p["bad"])
    assert not any("qatnashi yuqori" in x for x in p["good"])  # davomat kam — maqtalmaydi

    pdf = teacher_report.build_pdf(data)
    assert pdf.startswith(b"%PDF") and len(pdf) > 3000


def test_send_only_to_linked_bosh_menejer(make_user, world):  # noqa: F811
    from apps.notifications.models import TelegramLink

    TelegramLink.objects.create(user=make_user("BOSH_MENEJER"), chat_id=111)
    TelegramLink.objects.create(user=world["teacher"], chat_id=222)
    data = teacher_report.grade(teacher_report.collect(TODAY - datetime.timedelta(days=6), TODAY))
    sent = []
    assert teacher_report.send(data, b"%PDF-1.4", sender=lambda *a: sent.append(a)) == 1
    assert sent[0][0] == 111 and sent[0][1].startswith("ustozlar_") and "Ustozlar ish sifati" in sent[0][3]


def test_empty_period_and_command(tmp_path):
    assert teacher_report.report(datetime.date(2020, 1, 1), datetime.date(2020, 1, 31)).startswith(b"%PDF")
    out = tmp_path / "u.pdf"
    call_command("teacher_report", month="2020-02", out=str(out))
    assert out.read_bytes().startswith(b"%PDF")
