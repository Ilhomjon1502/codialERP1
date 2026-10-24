"""/api/v1/ marshrutlari."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts import views as acc
from apps.ai_assistant import views as ai
from apps.calls import views as calls
from apps.clientbot import views as clientbot
from apps.core import views as core
from apps.crm import views as crm
from apps.education import views as edu
from apps.finance import views as fin
from apps.notifications import views as notif
from apps.payroll import views as pay
from apps.references import views as ref
from apps.reports import views as rep
from apps.tasks import views as tasks

router = DefaultRouter(trailing_slash=True)
router.include_root_view = False
router.register("users", acc.UserViewSet, basename="user")
router.register("roles", acc.RoleViewSet, basename="role")
router.register("branches", ref.BranchViewSet, basename="branch")
router.register("courses", ref.CourseViewSet, basename="course")
router.register("rooms", ref.RoomViewSet, basename="room")
router.register("day-patterns", ref.DayPatternViewSet, basename="day-pattern")
router.register("lesson-times", ref.LessonTimeViewSet, basename="lesson-time")
router.register("course-prices", ref.CoursePriceViewSet, basename="course-price")
router.register("lesson-frequencies", ref.LessonFrequencyViewSet, basename="lesson-frequency")
router.register("discount-types", ref.DiscountTypeViewSet, basename="discount-type")
router.register("expense-categories", ref.ExpenseCategoryViewSet, basename="expense-category")
router.register("lead-sources", ref.LeadSourceViewSet, basename="lead-source")
router.register("attendance-statuses", ref.AttendanceStatusViewSet, basename="attendance-status")
router.register("accounts", ref.AccountViewSet, basename="account")
router.register("audit-log", ref.AuditLogViewSet, basename="audit-log")
router.register("leads", crm.LeadViewSet, basename="lead")
router.register("students", crm.StudentViewSet, basename="student")
router.register("parents", crm.ParentViewSet, basename="parent")
router.register("groups", edu.GroupViewSet, basename="group")
router.register("contracts", edu.ContractViewSet, basename="contract")
router.register("debtors", edu.DebtorViewSet, basename="debtor")
router.register("attendance", edu.AttendanceViewSet, basename="attendance")
router.register("makeups", edu.MakeupViewSet, basename="makeup")
router.register("evaluations", edu.TeacherEvaluationViewSet, basename="evaluation")
router.register("parent-calls", edu.ParentCallViewSet, basename="parent-call")
router.register("payments", fin.PaymentViewSet, basename="payment")
router.register("transfers", fin.TransferViewSet, basename="transfer")
router.register("exchanges", fin.ExchangeViewSet, basename="exchange")
router.register("expenses", fin.ExpenseViewSet, basename="expense")
router.register("creditors", fin.CreditorViewSet, basename="creditor")
router.register("creditor-transactions", fin.CreditorTxViewSet, basename="creditor-transaction")
router.register("kpi-rates", pay.KPIRateViewSet, basename="kpi-rate")
router.register("salary-assignments", pay.SalaryAssignmentViewSet, basename="salary-assignment")
router.register("salary-payouts", pay.SalaryPayoutViewSet, basename="salary-payout")
router.register("tasks", tasks.StaffTaskViewSet, basename="task")
router.register("calls", calls.CallRecordViewSet, basename="call")
router.register("call-devices", calls.CallDeviceViewSet, basename="call-device")
router.register("sms-templates", calls.SmsTemplateViewSet, basename="sms-template")
router.register("sms-rules", calls.SmsRuleViewSet, basename="sms-rule")
router.register("sms", calls.SmsMessageViewSet, basename="sms")
router.register("bot-links", clientbot.BotLinkViewSet, basename="bot-link")
router.register("bot-invites", clientbot.BotInviteViewSet, basename="bot-invite")
router.register("bot-surveys", clientbot.LeadSurveyViewSet, basename="bot-survey")
router.register("bot-referrals", clientbot.ReferralViewSet, basename="bot-referral")
router.register("bot-messages", clientbot.BotMessageViewSet, basename="bot-message")
router.register("bot-config", clientbot.BotConfigViewSet, basename="bot-config")

urlpatterns = [
    path("auth/csrf/", acc.CsrfView.as_view()),
    path("auth/login/", acc.LoginView.as_view()),
    path("auth/logout/", acc.LogoutView.as_view()),
    path("auth/me/", acc.MeView.as_view()),
    path("auth/password/reset/", acc.PasswordResetView.as_view()),
    path("auth/password/set/", acc.PasswordSetView.as_view()),
    path("auth/telegram/", notif.TelegramLoginView.as_view()),
    path("health/", core.health),
    path("bootstrap/", ref.bootstrap),
    path("approvals/", fin.approvals),
    path("kpi/", pay.kpi_tree),
    path("export/contracts/", edu.export_contracts),
    path("schedule/", edu.schedule),
    path("notifications/me/", notif.me),
    path("ai/", ai.info),
    path("ai/ask/", ai.ask),
    path("ai/<int:pk>/run/", ai.rerun),
    path("ai/<int:pk>/analyze/", ai.analyze),
    path("reports/profit/", rep.profit),
    path("reports/sheet/", rep.sheet),
    path("reports/stats/", rep.stats),
    path("reports/funnel/", rep.funnel),
    path("reports/first-payers/", rep.first_payers),
    path("kpi/rows/", pay.kpi_rows),
    path("calls/pair/", calls.PairView.as_view()),
    path("calls/ingest/", calls.IngestView.as_view()),
    path("calls/ping/", calls.PingView.as_view()),
    path("calls/sms/outbox/", calls.SmsOutboxView.as_view()),
    path("calls/sms/report/", calls.SmsReportView.as_view()),
    path("calls/sms/inbox/", calls.SmsInboxView.as_view()),
    *router.urls,
]
