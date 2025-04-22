from django.contrib import admin
from .models import Kindergarten
# Register your models here.

@admin.register(Kindergarten) # デコレータを使って登録
class KindergartenAdmin(admin.ModelAdmin):
    list_display = ('name', 'auth_code', 'prefecture', 'address', 'created_at') # 一覧に表示するフィールド
    search_fields = ('name', 'auth_code', 'address') # 検索ボックスで検索対象とするフィールド
    list_filter = ('prefecture',) # 右サイドバーに表示されるフィルタ項目models here.
