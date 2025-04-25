from django.urls import path
from . import views
from .views import ProfilePasswordEditView

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
    path('profile/name/edit/', views.profile_name_edit, name='profile_name_edit'),
    path('profile/display_name/edit/', views.profile_display_name_edit, name='profile_display_name_edit'),
    path('profile/email/edit/', views.profile_email_edit, name='profile_email_edit'),
    path('profile/password/edit/', ProfilePasswordEditView.as_view(), name='profile_password_edit'), # クラスベースビューは呼び出し方が異なる　view.as_view()
]