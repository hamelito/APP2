from django.contrib import admin
from tutorials.models import Tutorial

class TaskAdmin(admin.ModelAdmin):
    class TaskAdmin(admin.ModelAdmin):
        list_display=('title','thumb','description','date','published')
        read_only=('created_date')

admin.site.register(Tutorial,TaskAdmin)
# Register your models here.
