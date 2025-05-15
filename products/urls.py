from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    path('', views.product_list_view, name='top'),
    path('sell/', views.sell, name='sell'),
    path('detail/<int:pk>', views.detail, name='product_detail'),
    path('edit/<int:pk>', views.edit, name='product_edit'),
    path('delete/<int:pk>', views.delete, name='product_delete'),
]