"""Foyda → «Hisobot olish»: oylik moliyaviy hisobot Google Sheets'da (apps/reports/sheet_report.py, gsheets.py)."""

import base64
import datetime
import json

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.finance.models import Creditor, CreditorTransaction, Expense
from apps.payroll.models import SalaryAssignment
from apps.references.models import ExpenseCategory
from apps.reports import gsheets, services, sheet_report
from tests.test_finance import fin, pay  # noqa: F401 — fixture

pytestmark = pytest.mark.django_db
TODAY = timezone.localdate()
MONTH = TODAY.replace(day=1)
PREV = (MONTH - datetime.timedelta(days=1)).replace(day=1)


class FakeSheets:
    """Google'ni almashtiradi: varaqlar, so'rovlar va yozilgan qiymatlarni yodda saqlaydi."""

    def __init__(self, sheets=None, values=None):
        self.sheets = sheets if sheets is not None else [{"sheetId": 0, "title": "Sheet1"}]
        self.read = values or {}
        self.batches, self.written = [], []
        self.next_id = 100

    def install(self, monkeypatch, settings):
        settings.GOOGLE_SHEET_ID = "FILEID1234567890123456789012345"
        settings.GOOGLE_SERVICE_ACCOUNT_B64 = "x"
        monkeypatch.setattr(gsheets, "tabs", lambda: {"title": "Codial", "sheets": list(self.sheets)})
        monkeypatch.setattr(gsheets, "batch_update", self.batch_update)
        monkeypatch.setattr(gsheets, "values_get", self.values_get)
        monkeypatch.setattr(gsheets, "values_update", lambda data: self.written.extend(data))
        return self

    def batch_update(self, requests):
        self.batches.append(requests)
        replies = []
        for r in requests:
            if "addSheet" in r:
                p = dict(r["addSheet"]["properties"], sheetId=self.next_id)
                self.next_id += 1
                self.sheets.append({"sheetId": p["sheetId"], "title": p["title"]})
                replies.append({"addSheet": {"properties": p}})
            else:
                replies.append({})
            if "deleteSheet" in r:
                self.sheets = [s for s in self.sheets if s["sheetId"] != r["deleteSheet"]["sheetId"]]
        return {"replies": replies}

    def values_get(self, ranges):
        return [self.read.get(rg.split("!")[-1], []) for rg in ranges]

    def cell(self, a1):
        return next((w["values"][0][0] for w in self.written if w["range"].endswith("!" + a1)), None)

    def ranges(self):
        return {w["range"].split("!")[-1] for w in self.written}


@pytest.fixture
def data(fin, make_user):  # noqa: F811
    b = fin["branch"]
    util = fin["cat"]
    util.name = "Komunal"
    util.save()
    rent = ExpenseCategory.objects.create(name="Ijara")
    Expense.objects.create(branch=b, date=TODAY, category=util, name="Svet", quantity=2, price=150_000, total=300_000, cash_type="CASH", account=fin["cash"],
                           period_year=TODAY.year, period_month=TODAY.month, comment="avgust uchun")
    Expense.objects.create(branch=b, date=TODAY, category=rent, name="Ofis", quantity=1, price=4_800_000, total=4_800_000, cash_type="CASH", account=fin["cash"],
                           period_year=TODAY.year, period_month=TODAY.month)
    div = ExpenseCategory.objects.create(name="Dividend", kind="Dividend")
    Expense.objects.create(branch=b, date=TODAY, category=div, name="x", quantity=1, price=900_000, total=900_000, cash_type="CASH", account=fin["cash"],
                           period_year=TODAY.year, period_month=TODAY.month)
    staff = make_user("HISOBCHI")
    SalaryAssignment.objects.create(branch=b, user=fin["teacher"], year=TODAY.year, month=TODAY.month, fixed=2_000_000)
    SalaryAssignment.objects.create(branch=b, user=staff, year=TODAY.year, month=TODAY.month, fixed=1_000_000, fine=100_000)
    mnsh = Creditor.objects.create(name="MNSH")
    ilh = Creditor.objects.create(name="Ilhomjon Ibragimov")
    for cr, amt in ((mnsh, -3_000_000), (mnsh, 500_000), (ilh, -1_000_000)):
        CreditorTransaction.objects.create(date=TODAY, creditor=cr, amount=amt, cash_type="CASH", account=fin["cash"], cashier=fin["boss"])
    return {**fin, "staff": staff}


def test_collect_matches_profit_page(api, fin, data):  # noqa: F811
    pay(api(fin["cashier"]), fin, amount=1_000_000)
    d = sheet_report.collect(fin["boss"], MONTH)
    row = services.profit(fin["boss"], [MONTH])[0]
    assert d["income"] == row["payments"] == 1_000_000
    assert sum(e["total"] for e in d["expenses"]) == row["expenses"] == 5_100_000  # dividend kirmaydi
    assert sum(v for _, v in d["teachers"]) + sum(v for _, v in d["staff"]) == row["salaries"] == 2_900_000  # jarima ayirilgan
    assert [n for n, _ in d["teachers"]] == [fin["teacher"].full_name] and [n for n, _ in d["staff"]] == [data["staff"].full_name]
    assert [e["name"] for e in d["expenses"]] == ["Ijara", "Komunal"]  # namunadagi tartib
    assert "Svet — 2 × 150 000 = 300 000 · avgust uchun" in d["expenses"][1]["note"]
    # «−» qarz olish: MNSH 3 000 000 oldi, 500 000 qaytardi → 2 500 000; nom bo'yicha topiladi («Ilhomjon Ibragimov»)
    assert {h["label"]: h["taken"] for h in d["holders"]} == {"MNSH": 2_500_000, "Ilhomjon": 1_000_000}


HOLDERS = [{"label": "MNSH", "pct": 75, "taken": 3_350_000}, {"label": "Ilhomjon", "pct": 25, "taken": 5_195_000}]


def test_layout_formulas_and_manual_cells():
    d = {"month": MONTH, "income": 49_177_000, "teachers": [("Ali", 5_000_000)], "staff": [("Vali", 700_000)],
         "expenses": [{"name": "Ijara", "total": 4_760_000, "note": "izoh"}], "holders": HOLDERS}
    p = sheet_report.layout(d, {"income": 46_292_000, "pct": {5: 43.0, 9: 13.0}}, partial=True)
    c = p["cells"]
    assert p["list_end"] == 17 and p["total"] == 19  # namunadagidek
    assert c[(4, 2)] == "Ali" and c[(4, 3)] == 5_000_000 and c[(4, 4)] == "Vali" and c[(3, 8)] == "Ijara" and c[(3, 9)] == 4_760_000
    assert c[(18, 3)] == "=SUM(D5:D17)" and c[(18, 5)] == "=SUM(F5:F17)" and c[(18, 9)] == "=SUM(J4:J17)" and c[(19, 3)] == "=D19+F19"
    assert (c[(2, 13)], c[(4, 13)], c[(5, 13)], c[(6, 13)], c[(8, 13)]) == (49_177_000, "=D19", "=F19", "=J19", "=N3-N5-N6-N7")
    assert c[(11, 13)] == "=N9*0.75" and c[(12, 13)] == "=N9*0.25"
    assert c[(15, 12)] == "MNSH: " and c[(15, 13)] == 3_350_000 and c[(15, 15)] == "=N12-N16+O16"
    assert c[(16, 15)] == "=N13-N17+O17" and c[(2, 15)] == 46_292_000 and c[(4, 15)] == 43.0 and c[(5, 15)] == ""  # oldingi oy bo'lmagan qatorlar bo'sh
    assert p["notes"] == {(3, 9): "izoh"}
    assert (15, 14) in p["manual"] and (16, 14) in p["manual"] and (15, 14) not in c  # «avvalgi oydan» — qo'lda
    assert "hozirgacha" in c[(0, 2)]
    assert sheet_report._safe("=SUM(1)") == "'=SUM(1)"


def test_layout_grows_when_lists_are_long():
    d = {"month": MONTH, "income": 0, "teachers": [(f"U{i}", 1) for i in range(20)], "staff": [], "expenses": [], "holders": HOLDERS}
    p = sheet_report.layout(d)
    assert p["list_end"] == 24 and p["total"] == 26 and p["cells"][(25, 3)] == "=SUM(D5:D24)" and p["cells"][(26, 3)] == "=D26+F26"
    assert p["cells"][(4, 15)] == "" and p["cells"][(3, 15)] == ""  # «Avvalgi oyda» ustuni oldingi oysiz bo'sh


def test_generate_creates_tab_and_keeps_manual_cells(monkeypatch, settings, fin, data):  # noqa: F811
    f = FakeSheets().install(monkeypatch, settings)
    r = sheet_report.generate(fin["boss"], MONTH)
    title = sheet_report.tab_title(MONTH)
    assert r["created"] and r["partial"] and r["title"] == title and r["url"].endswith("#gid=100")
    assert any("addSheet" in x for batch in f.batches for x in batch)
    assert [s["title"] for s in f.sheets] == [title]  # bo'sh «Sheet1» o'chirilgan
    assert f.cell("N3") == 0 and f.cell("D5") == 2_000_000 and f.cell("J4") == 4_800_000 and f.cell("N16") == 2_500_000
    assert "O16" not in f.ranges() and "O17" not in f.ranges()  # qo'lda yoziladigan joyga tegilmaydi
    assert all(w["range"].startswith(f"'{title}'!") for w in f.written)
    notes = [x for batch in f.batches for x in batch if "updateCells" in x and x["updateCells"].get("rows")]
    assert any("Svet" in n["updateCells"]["rows"][0]["values"][0]["note"] for n in notes)  # xarajat izohi katakka note bo'lib

    # qayta bosilsa — varaq yaratilmaydi, yangilanadi
    f.batches.clear(), f.written.clear()
    r2 = sheet_report.generate(fin["boss"], MONTH)
    assert not r2["created"] and not any("addSheet" in x for batch in f.batches for x in batch) and f.cell("D5") == 2_000_000


def test_generate_reads_previous_month_percentages(monkeypatch, settings, fin, data):  # noqa: F811
    prev = sheet_report.tab_title(PREV)
    f = FakeSheets([{"sheetId": 0, "title": "Sheet1"}, {"sheetId": 7, "title": prev}],
                   {"N3": [[46_292_000]], "O3:O13": [[""], [""], [43.0], [16.0], [29.0], [""], [13.0], [""], [""], [10.0], [3.0]]}).install(monkeypatch, settings)
    sheet_report.generate(fin["boss"], MONTH)
    assert f.cell("P3") == 46_292_000 and f.cell("P5") == 43.0 and f.cell("P9") == 13.0 and f.cell("P12") == 10.0 and f.cell("P4") == "Avvalgi oyda"
    assert {s["title"] for s in f.sheets} == {prev, sheet_report.tab_title(MONTH)}  # bo'sh «Sheet1» o'chiriladi, oldingi oy varag'i qoladi


def test_future_month_and_not_configured(monkeypatch, settings, fin):  # noqa: F811
    FakeSheets().install(monkeypatch, settings)
    with pytest.raises(ValidationError):
        sheet_report.generate(fin["boss"], (MONTH + datetime.timedelta(days=40)).replace(day=1))
    settings.GOOGLE_SERVICE_ACCOUNT_B64 = ""
    with pytest.raises(gsheets.SheetsError, match="set-google.sh"):
        sheet_report.generate(fin["boss"], MONTH)


def test_api_permissions_and_errors(monkeypatch, settings, api, make_user, fin, data):  # noqa: F811
    FakeSheets().install(monkeypatch, settings)
    bm = api(fin["boss"])
    assert bm.get("/api/v1/reports/sheet/").json() == {"configured": True}
    r = bm.post("/api/v1/reports/sheet/", {"month": f"{TODAY:%Y-%m}"}, format="json")
    assert r.status_code == 200, r.content
    assert r.json()["created"] and "docs.google.com/spreadsheets/d/" in r.json()["url"]
    assert bm.post("/api/v1/reports/sheet/", {"month": "2099-01"}, format="json").status_code == 400
    for role in ("FILIAL_MENEJERI", "HISOBCHI", "ADMINISTRATOR"):
        assert api(make_user(role)).post("/api/v1/reports/sheet/", {}, format="json").status_code == 403

    def boom(*a, **k):
        raise gsheets.SheetsError("Google faylga ruxsat yo'q")
    monkeypatch.setattr(gsheets, "tabs", boom)
    r = bm.post("/api/v1/reports/sheet/", {}, format="json")
    assert r.status_code == 502 and "ruxsat" in r.json()["detail"]


def test_service_account_jwt_is_signed(monkeypatch, settings):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode()
    settings.GOOGLE_SERVICE_ACCOUNT_B64 = base64.b64encode(json.dumps({"type": "service_account", "client_email": "bot@x.iam.gserviceaccount.com", "private_key": pem}).encode()).decode()
    settings.GOOGLE_SHEET_ID = "ID"
    sent = {}

    def fake_http(method, url, body=None, headers=None, raw=False):
        sent.update(url=url, form=body.decode())
        return {"access_token": "tok", "expires_in": 3600}

    monkeypatch.setattr(gsheets, "_http", fake_http)
    gsheets._token.update(value=None, exp=0)
    assert gsheets.access_token() == "tok"
    assertion = sent["form"].split("assertion=")[1]
    head, claim, sig = assertion.split(".")
    pad = lambda s: s + "=" * (-len(s) % 4)  # noqa: E731
    key.public_key().verify(base64.urlsafe_b64decode(pad(sig)), f"{head}.{claim}".encode(), padding.PKCS1v15(), hashes.SHA256())  # imzo to'g'ri
    c = json.loads(base64.urlsafe_b64decode(pad(claim)))
    assert c["iss"] == "bot@x.iam.gserviceaccount.com" and c["scope"].endswith("/spreadsheets") and c["aud"] == gsheets.TOKEN_URL
    assert gsheets.access_token() == "tok"  # keshdan
    gsheets._token.update(value=None, exp=0)


def test_human_errors():
    assert "yoqilmagan" in gsheets._human(403, json.dumps({"error": {"message": "Google Sheets API has not been used in project 1"}}))
    assert "topilmadi" in gsheets._human(404, "{}")
    assert "Editor" in gsheets._human(403, json.dumps({"error": {"message": "The caller does not have permission"}}))
