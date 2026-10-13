from django.contrib import admin

from .models import Attendance, Contract, Group, MakeupRequest

for m in [Group, Contract, Attendance, MakeupRequest]:
    admin.site.register(m)
