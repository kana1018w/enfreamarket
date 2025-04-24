from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('signup/', views.signup, name='signup'),
    # maypage
    path('mypage/', views.mypage, name='mypage'),
    path('mypage/listings/',views.my_listings, name='my_listings'),
    path('mypage/intents/given/',views.my_intents_given, name='my_intents_given'),
    path('mypage/intents/received/',views.my_intents_received, name='my_intents_received'),
    path('profile_edit/', views.profile_edit, name='profile_edit'),
    path('password_change/', views.password_change, name='password_change'),

]