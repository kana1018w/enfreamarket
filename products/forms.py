# products/forms.py

from django import forms
from .models import Product, ProductCategory, ProductImage

class ProductForm(forms.ModelForm):
    """商品出品フォーム (メイン/サブ画像分離)"""

    # --- 商品名フィールド ---
    name = forms.CharField(
        label='商品名',
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': '例）〇〇幼稚園 制服 冬 上着',
            'class': 'form-control login-input',
        }),
        error_messages={
            'required': '商品名を入力してください。',
            'max_length': '商品名は100文字以内で入力してください。',
        }
    )

    # --- 価格フィールド ---
    price = forms.IntegerField( # PositiveIntegerFieldに対応するIntegerFieldを使用
        label='価格（円）',
        required=True,
        min_value=0, # マイナス値は許可しない
        widget=forms.NumberInput(attrs={
            'placeholder': '例）1500 (半角数字)',
            'class': 'form-control login-input',
            'min': '0', # HTML属性としても設定
        }),
        error_messages={
            'required': '価格を入力してください。',
            'invalid': '有効な数値を入力してください。', 
            'min_value': '価格は0円以上で入力してください。',
        },
        help_text='半角数字で入力してください。'
    )

    # --- カテゴリ選択フィールド ---
    product_category = forms.ModelChoiceField(
        label=Product._meta.get_field('product_category').verbose_name, # モデルの verbose_name を利用
        queryset=ProductCategory.objects.all().order_by('id'), # 有効なカテゴリすべてを選択肢に (名前順)
        widget=forms.RadioSelect,
        required=True,
        initial=ProductCategory.objects.first(), # とりあえず最初のカテゴリを選択
        error_messages={'required': 'カテゴリを選択してください。'}
    )

    # --- サイズ選択フィールド ---
    size = forms.TypedChoiceField(
        label=Product._meta.get_field('size').verbose_name,
        choices=Product.Size.choices, # モデルの choices を利用
        required=True, # サイズ選択は必須　　（NO_SIZE でも可）
        widget=forms.RadioSelect,
        coerce=int, # 値を int に変換
        initial=Product.Size.NO_SIZE, # デフォルト値 
        error_messages={'required': 'サイズを選択してください。'}
    )

    # --- 状態選択フィールド ---
    condition = forms.TypedChoiceField(
        label=Product._meta.get_field('condition').verbose_name,
        choices=Product.Condition.choices, # モデルの choices を利用
        required=True,
        widget=forms.RadioSelect,
        coerce=int, 
        initial=Product.Condition.USED_NO_SCRATCH, # デフォルト値 (任意)
        error_messages={'required': '商品の状態を選択してください。'}
    )

    # --- 商品説明フィールド ---
    description = forms.CharField(
        label=Product._meta.get_field('description').verbose_name,
        required=False, # 説明文は任意
        widget=forms.Textarea(attrs={
            'placeholder': '商品の状態、購入時期、使用頻度などを入力してください。\n例）2年前に購入し、1年間着用しました。目立った汚れはありませんが、袖口に若干の毛玉があります。',
            'rows': 5, # 表示行数を指定
            'class': 'form-control login-input',
        })
        # 任意入力なので error_messages.required エラーメッセージは不要
    )

    # --- メイン画像フィールド ---
    main_image = forms.ImageField(
        label='メイン画像',
        required=False, # 編集画面の実装の関係で一旦False, init method で商品登録時はTrue に変更
        error_messages={'required': 'メイン画像を登録してください。'},
        widget=forms.FileInput(attrs={'class': 'form-control main-image'}),
        help_text='メイン画像の登録は必須です。' # clean_sub_images で枚数制限 
    )

    # --- サブ画像フィールド ---
    sub_images = forms.ImageField(
        label='サブ画像',
        required=False,
        widget=forms.FileInput(
            attrs={
                'class': 'form-control sub-images' # 必要に応じてクラス追加
            }
        ),
        help_text='サブ画像の登録は任意です。最大3枚までアップロードできます。' # clean_sub_images で枚数制限
    )


    class Meta:
        model = Product
        # モデルのフィールドとフォームフィールドを紐付ける
        # 上で明示的に定義したフィールド名をここにリストアップする
        fields = [
            'name',
            'price',
            'product_category',
            'size',
            'condition',
            'description',
            # main_image, sub_images はモデル外なので含めない
        ]

    def __init__(self, *args, **kwargs):
        """フォーム初期化時に編集かどうかを判定し、画像フィールドの必須属性等を調整"""
        # 親クラスの __init__ を呼び出す前に instance があるか確認
        is_edit = kwargs.get('instance') is not None
        super().__init__(*args, **kwargs) # 親クラスの初期化

        # is_edit フラグに基づいて main_image の設定を変更
        # 一旦 編集では写真の編集機能を実装しないので、main_image を非必須にする
        if is_edit:
            self.fields['main_image'].required = False
            self.fields['main_image'].help_text = '現在の画像を変更する場合のみ、新しい画像をアップロードしてください。'
        else:
            # 新規出品時
            self.fields['main_image'].required = True
            self.fields['main_image'].error_messages = {'required': 'メイン画像を登録してください。'}
            self.fields['main_image'].help_text = 'メイン画像の登録は必須です。'

    # --- サブ画像の枚数チェック (前回と同様) ---
    def clean_sub_images(self):
        """サブ画像の枚数をバリデーション (最大3枚)"""
        sub_images = self.files.getlist('sub_images')
        MAX_SUB_IMAGES = 3
        if len(sub_images) > MAX_SUB_IMAGES:
            raise forms.ValidationError(f'サブ画像は最大 {MAX_SUB_IMAGES} 枚までアップロードできます。アップロードされたファイル数: {len(sub_images)}')
        return sub_images

    # --- 全体に関わるバリデーション は特にないのでcleanメソッドは定義しない ---