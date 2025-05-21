from django.db import models
from django.conf import settings # AUTH_USER_MODEL を参照するために必要
from django.utils import timezone

# accountsアプリのKindergartenモデルをインポート
try:
    from accounts.models import Kindergarten
except ImportError:
    # 暫定: accountsアプリが見つからない場合やテスト用に仮定義
    from django.db import models as mock_models
    class Kindergarten(mock_models.Model):
        name = mock_models.CharField(max_length=100)
        def __str__(self): return self.name
        # 他に必要なフィールドがあれば追加


# --- 商品カテゴリモデル ---
class ProductCategory(models.Model):
    """商品カテゴリ"""
    name = models.CharField(
        'カテゴリ名',
        max_length=50,
        unique=True # カテゴリ名は重複しない
    )
    created_at = models.DateTimeField('登録日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        db_table = 'product_categories'
        verbose_name = 'カテゴリ'
        verbose_name_plural = 'カテゴリ' # 複数形もカテゴリ

    def __str__(self):
        return self.name


# --- 商品画像モデル ---
class ProductImage(models.Model):
    """商品画像"""
    product = models.ForeignKey(
        'Product', #循環参照のエラーを回避するため文字列で指定
        on_delete=models.CASCADE, # 商品削除時に画像も削除
        related_name='images', # Productから画像を参照する際の名前 (例: product.images.all)
        verbose_name='商品'
    )
    image = models.ImageField(
        '画像ファイル',
        upload_to='product_images/' # 画像ファイルのアップロード先ディレクトリ
    )
    display_order = models.IntegerField(
        '表示順',
        default=0,
        help_text='数字が小さいほど先に表示されます。'
    )
    created_at = models.DateTimeField('登録日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        db_table = 'product_images'
        verbose_name = '商品画像'
        verbose_name_plural = '商品画像'
        ordering = ['product','display_order']

    def __str__(self):
        return f'{self.product.name} - 画像{self.id}'

# --- 商品モデル ---
class Product(models.Model):
    """出品される商品"""

    # --- 状態の選択肢 ---
    class Condition(models.IntegerChoices):
        # 属性名 = 'DB保存値', '表示ラベル'
        NEW = 1, '新品、未使用'
        ALMOST_UNUSED = 2, '未使用に近い'
        USED_NO_SCRATCH = 3, '目立った傷や汚れなし'
        USED_SLIGHTLY_SCRATCHED = 4, 'やや傷や汚れあり'
        BAD = 5, '全体的に状態が悪い'

    # --- 商品ステータスの選択肢 ---
    class Status(models.IntegerChoices):
        FOR_SALE = 1, '販売中'
        IN_TRANSACTION = 2, '取引中'
        SOLD = 3, '売却済'

    class Size(models.IntegerChoices):
        NO_SIZE = 0, '選択しない'
        SIZE_80 = 80, '80'
        SIZE_90 = 90, '90'
        SIZE_100 = 100, '100'
        SIZE_110 = 110, '110'
        SIZE_120 = 120, '120'
        SIZE_130 = 130, '130'
        SIZE_140 = 140, '140'
        SIZE_140_PLUS = 141, '140以上'
        S = 201, 'S'
        M = 202, 'M'
        L = 203, 'L'
        FREE = 999, 'Free'

    # --- フィールド定義 ---
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, # settings.AUTH_USER_MODEL を使うのが推奨
        on_delete=models.CASCADE, # ユーザー削除時に商品も削除
        related_name='products',
        verbose_name='出品者'
    )
    kindergarten = models.ForeignKey(
        Kindergarten,
        on_delete=models.PROTECT, # 園が削除されても商品は残す (要件による)
        related_name='products',
        verbose_name='関連園',
        editable=False # 通常、出品時にユーザーの所属園から自動設定し、編集不可にする
    )
    product_category = models.ForeignKey(
        ProductCategory,
        on_delete=models.PROTECT, # カテゴリ削除時に商品は残す (要件による)
        related_name='products',
        verbose_name='カテゴリ',

    )
    name = models.CharField('商品名', max_length=100)
    price = models.PositiveIntegerField('価格') # 価格は通常0以上なので PositiveIntegerField
    size = models.IntegerField(
        'サイズ',
        choices=Size.choices,
        default=Size.NO_SIZE
    )
    condition = models.IntegerField(
        '商品の状態',
        choices=Condition.choices,
        default=Condition.USED_NO_SCRATCH
    )

    description = models.TextField('商品説明', blank=True, max_length=500) # 説明文は任意入力が多い
    status = models.IntegerField(
        'ステータス',
        choices=Status.choices,
        default=Status.FOR_SALE # 出品時は基本的に販売中
    )
    negotiating_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, # 取引相手が削除されても商品は残す
        related_name='negotiating_products',
        verbose_name='取引相手',
        null=True, # 取引前はNULL
        blank=True # フォームでも空欄OK
    )
    main_product_image = models.ForeignKey(
        'ProductImage', #循環参照のエラーを回避するため文字列で指定
        on_delete=models.SET_NULL, # メイン画像削除時はNULLに
        related_name='+',          # 逆参照不要
        verbose_name='メイン画像',
        null=True,                 # NULL許可
        blank=True,                # 空欄許可
        editable=False             # ビューで設定するので編集不可を推奨
    )
    created_at = models.DateTimeField('出品日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        db_table = 'products'
        verbose_name = '商品'
        verbose_name_plural = '商品'
        ordering = ['-created_at'] # 新しい順に並べるのをデフォルトにする (任意)

    def __str__(self):
        return f'{self.name} (¥{self.price}) {self.size} / {self.product_category} / {self.condition}'

    def get_sub_image_by_display_order(self, order):
        """指定された display_order のサブ画像 (メイン画像以外) を取得する。なければ None を返す。"""
        try:
            # メイン画像は display_order=0 と仮定
            if order == 0: # display_order=0 はメイン画像なので除外
                return None
            return self.images.get(display_order=order)
        except ProductImage.DoesNotExist:
            return None

    def get_sub_images_as_dict(self):
        """サブ画像を display_order をキーとした辞書として取得する (1, 2, 3)"""
        sub_images_dict = {}
        # メイン画像を除外し、display_order が 1, 2, 3 のものを対象とする
        images = self.images.filter(display_order__in=[1, 2, 3]).order_by('display_order')
        for img in images:
            sub_images_dict[img.display_order] = img
        
        # 存在しない display_order のキーも None で埋めておく (テンプレートでの扱いを容易にするため)
        for i in range(1, 4): # 1, 2, 3
            if i not in sub_images_dict:
                sub_images_dict[i] = None
        return sub_images_dict


