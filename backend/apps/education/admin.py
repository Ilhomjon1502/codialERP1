from django.contrib import admin

from .models import Attendance, Contract, GradingSession, Group, MakeupRequest, ParentCall, StudentGrade, TeacherEvaluation

for m in [Group, Contract, Attendance, MakeupRequest, TeacherEvaluation, GradingSession, StudentGrade, ParentCall]:
    admin.site.register(m)
