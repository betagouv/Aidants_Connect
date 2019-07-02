from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Usager, Mandat

admin.site.register(User, UserAdmin)
admin.site.register(Usager)
admin.site.register(Mandat)
