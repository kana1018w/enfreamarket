from django.contrib import admin

# accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin # 標準のUserAdminをインポート
from .models import User # 作成したカスタムUserモデルをインポート

# 標準のUserAdminを継承してカスタムUserモデル用に設定を追加・変更
class UserAdmin(BaseUserAdmin):
    # 管理画面の一覧ページに表示するフィールド
    list_display = ('email', 'name', 'display_name', 'kindergarten', 'is_staff', 'is_active', 'created_at', 'updated_at')
    # 管理画面の一覧ページでリンクになるフィールド
    list_display_links = ('email', 'name')
    # 絞り込みに使うフィールド
    list_filter = ('is_staff', 'is_active', 'kindergarten') # 幼稚園でも絞り込めるように
    # 編集画面でのフィールド構成 (標準のものをベースにカスタマイズ)
    fieldsets = (
        (None, {'fields': ('email', 'password')}), # emailとパスワード
        ('Personal info', {'fields': ('name', 'display_name', 'kindergarten')}), # 個人情報（園、名前、表示名を追加）
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',
                                   'groups', 'user_permissions')}), # 権限関連
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}), # 日時関連 (created_at, updated_at を追加)
    )
    # 編集画面の上部に表示される読み取り専用フィールド
    readonly_fields = ('last_login', 'created_at', 'updated_at')
    # 検索ボックスの対象フィールド
    search_fields = ('email', 'name', 'display_name')
    # 一覧ページの表示順
    ordering = ('email',)
    # パスワードフィールドは編集画面に直接表示しない (ハッシュ化されるため)
    # filter_horizontal = ('groups', 'user_permissions',) # グループや権限が多い場合に便利

# 作成したUserAdmin設定を使ってUserモデルを管理サイトに登録
admin.site.register(User, UserAdmin)
