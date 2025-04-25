from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('terms/', views.terms, name='terms'),
]