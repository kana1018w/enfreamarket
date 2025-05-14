from django.urls import path
from . import views

app_name = 'interactions'

urlpatterns = [
    path('product/<int:product_pk>/comment/add/', views.add_comment, name='add_comment'),
    # お気に入り一覧ページ
    path('favorites/', views.favorite_list, name='favorite_list'),
    # お気に入り登録/解除
    path('product/<int:product_pk>/favorite_toggle/', views.favorite_toggle, name='favorite_toggle'),

    # 購入意思表示
    path('product/<int:product_pk>/purchase_intent/add/', views.add_purchase_intent, name='add_purchase_intent'),
    path('product/<int:product_pk>/purchase_intent/delete/', views.delete_purchase_intent, name='delete_purchase_intent'),
    path('purchase_intents/received/', views.received_purchase_intents_list, name='received_purchase_intents_list'),
    path('purchase_intents/sent/', views.sent_purchase_intents_list, name='sent_purchase_intents_list'),

    # 取引
    path('purchase_intent/<int:intent_pk>/start_transaction/', views.start_transaction, name='start_transaction'),
]