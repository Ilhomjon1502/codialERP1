from django.contrib import admin

from . import models

for m in [models.Branch, models.Course, models.Room, models.DayPattern, models.LessonTime, models.CoursePrice,
          models.LessonFrequency, models.DiscountType, models.ExpenseCategory, models.LeadSource, models.AttendanceStatus]:
    admin.site.register(m)
