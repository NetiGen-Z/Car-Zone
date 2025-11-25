# payments/urls.py

from django.urls import path, re_path
from . import views

app_name = 'payments'

urlpatterns = [
    path('initiate/<int:car_id>/', views.initiate_payment, name='initiate_payment'),
    re_path(r'^verify(?:/(?P<car_id>[0-9]+))?/$', views.verify_payment, name='verify_payment'),
]
