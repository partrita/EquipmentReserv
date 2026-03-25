from django.urls import path
from . import views

from typing import List, Union
from django.urls.resolvers import URLPattern, URLResolver

urlpatterns: List[Union[URLPattern, URLResolver]] = [
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/',views.logout, name='logout'),
    path('activate/<str:uidb64>/<str:token>/', views.activate, name="activate"),
    path('confirm/', views.confirm, name="confirm"),
    path('password_reset/', views.MyPasswordResetView.as_view(), name='password_reset'),
    path('reset/<uidb64>/<token>/', views.MyPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
]
