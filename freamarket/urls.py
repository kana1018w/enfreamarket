from django.urls import path
from . import views

app_name = 'freamarket'

urlpatterns = [
    path('', views.index, name='index'),
    path('terms/', views.terms, name='terms'),
]