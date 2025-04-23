# accounts/models.py
from django.db import models
from django.contrib.auth.models import (
    BaseUserManager, AbstractBaseUser, PermissionsMixin, Group, Permission # Group, Permission をインポート
)
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
# 正しいパスから Kindergarten をインポートしてください
# 例: from kindergartens.models import Kindergarten
try:
    # アプリが別の場合
    from kindergartens.models import Kindergarten
except ImportError:
    # 同じアプリ内にある場合 (テスト用など)
    class Kindergarten(models.Model): # 仮定義 (本来はimport)
        name = models.CharField(max_length=100)
        def __str__(self): return self.name

# カスタムユーザーマネージャー 
class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, name=None, kindergarten=None, **other_fields):
        if not email:
            raise ValueError('The Email field must be set')
        # is_superuser フラグで必須チェックを分岐
        if not other_fields.get('is_superuser'):
             if not name:
                 raise ValueError('一般ユーザーには名前が必須です')
             if not kindergarten:
                 raise ValueError('一般ユーザーには所属園が必須です')
        elif not name: # スーパーユーザーでも name は必須とする
             raise ValueError('スーパーユーザーには名前が必須です')

        # メールアドレスの正規化
        email = self.normalize_email(email)

        # ForeignKey (kindergarten) の処理 (もしIDで渡されたらインスタンスを取得)
        if kindergarten and isinstance(kindergarten, int):
            try:
                kindergarten = Kindergarten.objects.get(pk=kindergarten)
            except Kindergarten.DoesNotExist:
                # 一般ユーザー登録時に不正なIDが渡された場合
                # スーパーユーザー作成時は None を許容
                if not other_fields.get('is_superuser'):
                    raise ValueError('無効な幼稚園IDです')
                else:
                   kindergarten = None # IDが見つからなくてもスーパーユーザーならNone

        # is_staff, is_superuser は other_fields で受け取る
        other_fields.setdefault('is_staff', False)
        other_fields.setdefault('is_superuser', False)

        user = self.model(
            email=email,
            name=name,
            kindergarten=kindergarten, # スーパーユーザー作成時はNoneの場合あり
            **other_fields
        )
        # ハッシュ化して保存
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        # username 引数は受け取らない (コマンドが渡そうとしてもextra_fieldsで吸収)
        extra_fields.pop('username', None) # 不要な username が渡された場合捨てる

        if not email:
            raise ValueError('Superuser must have an email address.')

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('スーパーユーザーは is_staff=True である必要があります。')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('スーパーユーザーは is_superuser=True である必要があります。')

        name = extra_fields.get('name')
        if not name:
             raise ValueError('スーパーユーザーには名前が必要です。')


        # kindergarten は None で create_user に渡す
        kindergarten = None

        # create_user を呼び出す
        return self.create_user(
            email=email,
            password=password,
            name=name,
            kindergarten=kindergarten,
            **extra_fields
        )

# カスタムユーザーモデル
class User(AbstractBaseUser, PermissionsMixin):
    # --- フィールド定義 ---
    kindergarten = models.ForeignKey(
        Kindergarten,
        on_delete=models.PROTECT,
        verbose_name='所属園',
        related_name='users',
        null=True, blank=True # スーパーユーザー用に一時的にNULLを許可する場合はコメント解除
    )
    name = models.CharField('名前', max_length=100) # null=False, blank=False はデフォルト
    display_name = models.CharField('表示名', max_length=50, null=True, blank=True)
    email = models.EmailField('メールアドレス', unique=True)
    # password フィールドは AbstractBaseUser が持っているので再定義しない！

    # --- Django認証システム用フィールド ---
    is_staff = models.BooleanField('スタッフ権限', default=False)
    is_active = models.BooleanField('アクティブ', default=True)

    # --- タイムスタンプ ---
    created_at = models.DateTimeField('登録日時', auto_now_add=True) # auto_now_add=True に変更推奨
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    # --- 権限関連 (related_name を指定) ---
    groups = models.ManyToManyField(
        Group,
        verbose_name=_('groups'),
        blank=True,
        related_name="user_custom_set", # 衝突回避
        related_query_name="user",
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name=_('user permissions'),
        blank=True,
        related_name="user_custom_set", # 衝突回避
        related_query_name="user",
    )

    # --- マネージャー、設定 ---
    objects = CustomUserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name','kindergarten'] 

    # --- メソッド ---
    def __str__(self):
        # return self.display_name or self.email # 表示名があればそれを、なければemail
        return self.email # emailを返すのが一般的

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.display_name or self.name