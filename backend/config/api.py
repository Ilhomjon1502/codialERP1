"""/api/v1/ marshrutlari."""

from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.accounts import views as acc
from apps.crm import views as crm
from apps.education import views as edu
from apps.finance import views as fin
from apps.payroll import views as pay
from apps.references import views as ref

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
router.register("gradings", edu.GradingSessionViewSet, basename="grading")
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

urlpatterns = [
    path("auth/csrf/", acc.CsrfView.as_view()),
    path("auth/login/", acc.LoginView.as_view()),
    path("auth/logout/", acc.LogoutView.as_view()),
    path("auth/me/", acc.MeView.as_view()),
    path("auth/password/reset/", acc.PasswordResetView.as_view()),
    path("auth/password/set/", acc.PasswordSetView.as_view()),
    path("bootstrap/", ref.bootstrap),
    path("approvals/", fin.approvals),
    path("kpi/", pay.kpi_tree),
    path("export/contracts/", edu.export_contracts),
    path("kpi/rows/", pay.kpi_rows),
    *router.urls,
]
