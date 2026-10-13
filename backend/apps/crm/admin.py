from django.contrib import admin

from .models import Lead, LeadComment, Parent, Student

for m in [Parent, Student, Lead, LeadComment]:
    admin.site.register(m)
