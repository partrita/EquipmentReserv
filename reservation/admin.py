from django.contrib import admin
from .models import Reservation, Blog, Equipment

# Register your models here.
admin.site.register(Reservation)
admin.site.register(Blog)
admin.site.register(Equipment)