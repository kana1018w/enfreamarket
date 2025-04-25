from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.index, name='index'),
    path('sell/', views.sell, name='sell'),
    path('favorite_list/', views.favorite_list, name='favorite_list'),
]