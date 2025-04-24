# accounts/forms.py
from django import forms
from .models import User 
from kindergartens.models import Kindergarten
from django.db import models 
from django.contrib.auth.forms import AuthenticationForm

# Kindergartenモデルもインポート（実際のパスに合わせてください）
try:
    from kindergartens.models import Kindergarten
except ImportError:
    # 仮定義 (テスト用など)
    class Kindergarten(models.Model):
        name = models.CharField(max_length=100)
        auth_code = models.CharField(max_length=50)
        objects = models.Manager() # objectsマネージャーが必要

class EmailAuthenticationForm(AuthenticationForm):
    """
    メールアドレス認証用のログインフォーム
    """
    # 標準の username フィールドを上書きして EmailField にする
    username = forms.EmailField(
        label="メールアドレス",
        widget=forms.EmailInput(attrs={'autofocus': True, 'class': 'form-control login-input', 'placeholder': '登録したメールアドレス'}),
        error_messages={'required': 'メールアドレスを入力してください。'}
    )

    password = forms.CharField(
        label="パスワード",
        strip=False,
        widget=forms.PasswordInput(attrs={'autocomplete': 'current-password', 'class': 'form-control login-input', 'placeholder': 'パスワード'}),
        error_messages={'required': 'パスワードを入力してください。'}
    )

    # error_messages をカスタマイズする場合 (任意)
    error_messages = {
        'invalid_login': "メールアドレスまたはパスワードが正しくありません。",
        'inactive': "このアカウントは無効です。",
    }

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(request=request, *args, **kwargs)
        # パスワードフィールドのラベルなどを変更したい場合 (任意)
        # self.fields['password'].label = "パスワード"

class SignUpForm(forms.Form):
    """
    アカウント新規登録用フォーム
    """
    # モデルフィールドに対応するフィールド
    name = forms.CharField(
        label='名前',
        max_length=100,
        required=True, # 必須項目
        widget=forms.TextInput(attrs={'class': 'form-control login-input','placeholder': '山田 太郎'}),
        error_messages={'required': 'お名前を入力してください。'}
    )
    display_name = forms.CharField(
        label='表示名（ニックネーム）',
        max_length=50,
        required=False, # 任意項目
        widget=forms.TextInput(attrs={'class': 'form-control login-input','placeholder': '（任意）他の人から見える名前です'})
    )
    email = forms.EmailField(
        label='メールアドレス',
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control login-input','placeholder': 'xxx@example.com'}),
        error_messages={'required': 'メールアドレスを入力してください。'} 
    )
    # モデルにはない確認用フィールド
    email2 = forms.EmailField(
        label='メールアドレス（確認）',
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control login-input','placeholder': '確認のためもう一度入力してください'}),
        error_messages={'required': '確認用メールアドレスを入力してください。'}
    )
    # パスワードフィールド (PasswordInputで入力が隠される)
    password = forms.CharField(
        label='パスワード',
        min_length=8, # 例: 最低8文字 (必要に応じて変更)
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control login-input','placeholder': '8文字以上入力してください'}),
        error_messages={'required': 'パスワードを入力してください。'}
    )
    # モデルにはない確認用フィールド
    password2 = forms.CharField(
        label='パスワード（確認）',
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control login-input','placeholder': '確認のためもう一度入力してください'}),
        error_messages={'required': '確認用パスワードを入力してください。'}
    )
    # 所属園フィールド (プルダウン選択)
    kindergarten = forms.ModelChoiceField(
        label='所属園',
        queryset=Kindergarten.objects.exclude(name='root園'), # ★ "root園" を除外
        required=True,
        empty_label='園を選択してください', # 未選択時の表示
        widget=forms.Select(attrs={'class': 'form-select login-input'}),
        error_messages={'required': '所属園を選択してください。'}
    )
    # モデルにはない認証コードフィールド
    auth_code = forms.CharField(
        label='認証コード',
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control login-input','placeholder': '園から配布された認証コードを入力してください'}),
        error_messages={'required': '認証コードを入力してください。'}
    )

    # --- バリデーションメソッド ---

    def clean_email(self):
        """メールアドレスのチェック"""
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("このメールアドレスは既に使用されています。")
        return email

    def clean_email2(self):
        """メールアドレス確認用フィールドのチェック"""
        email = self.cleaned_data.get('email')
        email2 = self.cleaned_data.get('email2')
        if email and email2 and email != email2:
            raise forms.ValidationError("メールアドレスが一致しません。")
        # 確認用フィールドの値は保存時には不要なので、Noneを返すか、
        # またはビュー側で使わないようにする。ここではemail2をそのまま返す。
        return email2

    def clean_password(self):
        password = self.cleaned_data.get('password')
        # ここで複雑性チェックのロジックを実装
        if len(password) < 8: # Djangoの標準バリデータと重複するが例として
             raise forms.ValidationError("パスワードは8文字以上で入力してください。")
        # 他のチェック (数字を含むか、など)
        return password
    
    def clean_password2(self):
        """パスワード確認用フィールドのチェック"""
        password = self.cleaned_data.get('password')
        password2 = self.cleaned_data.get('password2')
        if password and password2 and password != password2:
            raise forms.ValidationError("パスワードが一致しません。")
        # 確認用パスワードは保存には使わない
        return password2

    def clean(self):
        """フォーム全体のバリデーション (認証コードチェックなど)"""
        cleaned_data = super().clean() # まず親クラスのcleanメソッドを呼ぶ
        kindergarten = cleaned_data.get('kindergarten')
        auth_code = cleaned_data.get('auth_code')

        # 幼稚園が選択され、認証コードも入力されている場合のみチェック
        if kindergarten and auth_code:
            # 選択された幼稚園の正しい認証コードと比較
            if kindergarten.auth_code != auth_code:
                # 特定のフィールド ('auth_code') にエラーを紐付ける
                self.add_error('auth_code', "認証コードが選択された園のものと一致しません。")

        return cleaned_data 

class NameChangeForm(forms.ModelForm):
    """
    ユーザーの名前変更用フォーム
    """
    class Meta:
        model = User       # 対象モデルは User
        fields = ('name',) # 編集するフィールド

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # フィールドのラベルやウィジェットをカスタマイズ
        self.fields['name'].label = '変更後の名前'
        self.fields['name'].required = True # 名前の入力を必須にする
        self.fields['name'].widget = forms.TextInput(
            attrs={
                'class': 'form-control login-input',
            }
        )
        # 必須エラーメッセージをカスタマイズ (任意)
        self.fields['name'].error_messages = {
            'required': '名前を入力してください。'
        }