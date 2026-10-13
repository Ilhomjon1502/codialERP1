from django.contrib import admin

from .models import KPIRate, SalaryAssignment, SalaryPayout

for m in [KPIRate, SalaryAssignment, SalaryPayout]:
    admin.site.register(m)
