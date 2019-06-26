from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Demarche, Usager, Mandat

admin.site.register(User, UserAdmin)
admin.site.register(Demarche)
admin.site.register(Usager)
admin.site.register(Mandat)
