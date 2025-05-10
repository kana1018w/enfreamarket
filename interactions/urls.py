from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    path('product/<int:product_pk>/comment/add/', views.add_comment, name='add_comment'),
]