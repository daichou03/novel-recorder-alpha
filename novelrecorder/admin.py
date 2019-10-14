from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from novelrecorder import models

# Register your models here.
admin.site.register(models.NovelUser, UserAdmin)

admin.site.register(models.Novel)
admin.site.register(models.Character)
admin.site.register(models.Relationship)
admin.site.register(models.Description)
admin.site.register(models.NovelUserPermissionModel)
