from django.contrib import admin
from .models import ExamSession, Question,Submission

admin.site.register(Question)
# Register your models here.
admin.site.register(ExamSession)

admin.site.register(Submission)
