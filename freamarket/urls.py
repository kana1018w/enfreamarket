from django.urls import path
from . import views

app_name = 'freamarket'

urlpatterns = [
    path('', views.index, name='index'),
    path('sell/', views.sell, name='sell'),
    path('favorite_list/', views.favorite_list, name='favorite_list'),
    path('terms/', views.terms, name='terms'),
]