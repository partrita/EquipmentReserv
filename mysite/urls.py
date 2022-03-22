""" URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
import reservation.views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', reservation.views.home, name='home'),
    path('blog/<int:blog_id>', reservation.views.detail, name="detail"),
    path('reservation/new/<str:room_type>', reservation.views.new, name="new"),
    path('reservation/check', reservation.views.check, name="check"),
    path('reservation/index/<str:category_name>', reservation.views.index, name="index"),
    path('reservation/create', reservation.views.create, name='create'),
    path('reservation/edit/<int:reservation_id>', reservation.views.edit, name="edit"),
    path('reservation/update/<int:reservation_id>', reservation.views.update, name="update"),
    path('reservation/delete/<int:reservation_id>', reservation.views.delete, name="delete"),
    path('reservation/my', reservation.views.myreservation, name="myreservation"),
    path('accounts/',include('accounts.urls')), # Accounts
    path('ckeditor/', include('ckeditor_uploader.urls')), # ckeditor
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)