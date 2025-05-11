from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    path('product/<int:product_pk>/comment/add/', views.add_comment, name='add_comment'),
    # お気に入り一覧ページ
    path('favorites/', views.favorite_list, name='favorite_list'),
    # お気に入り登録/解除
    path('product/<int:product_pk>/favorite_toggle/', views.favorite_toggle, name='favorite_toggle'),
]