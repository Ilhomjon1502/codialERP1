from django.contrib import admin

from .models import Attendance, Contract, Group, MakeupRequest, ParentCall, TeacherEvaluation

for m in [Group, Contract, Attendance, MakeupRequest, TeacherEvaluation, ParentCall]:
    admin.site.register(m)
