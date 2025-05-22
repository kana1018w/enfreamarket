# products/forms.py

from django import forms
from .models import Product, ProductCategory, ProductImage

class ProductForm(forms.ModelForm):
    """商品出品フォーム"""

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
        initial=lambda: ProductCategory.objects.first(), # とりあえず最初のカテゴリを選択
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
        label='メイン',
        required=False, # 編集画面の実装の関係で一旦False, init method で商品登録時はTrue に変更
        error_messages={'required': 'メイン写真を登録してください。'},
        widget=forms.FileInput(attrs={'class': 'form-control form-img-input main-image'}),
    )

    # --- サブ画像フィールド (1枚ずつ, 3枚まで) ---
    sub_image_1 = forms.ImageField(
        label='1枚目',
        required=False, # 任意
        widget=forms.FileInput(attrs={'class': 'form-control form-img-input sub-image'}),
        help_text='サブ画像の登録は任意です。最大3枚まで登録可能です。'
    )
    sub_image_2 = forms.ImageField(
        label='2枚目',
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control form-img-input sub-image'}),
    )
    sub_image_3 = forms.ImageField(
        label='3枚目',
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control form-img-input sub-image'}),
    )

    # 編集時の写真更新に関する共通ヘルプテキスト
    image_update_help_text ='現在の写真を変更する場合は、新しい写真をアップロードしてください。空のまま送信すると現在の写真が維持されます。'

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
        if is_edit:
            self.fields['main_image'].required = False
        else:
            # 新規出品時
            self.fields['main_image'].required = True
            self.fields['main_image'].error_messages = {'required': 'メイン画像を登録してください。'}
            self.fields['main_image'].help_text = 'メイン画像の登録は必須です。'

    # --- 全体に関わるバリデーション は特にないのでcleanメソッドは定義しない ---


class ProductSearchForm(forms.Form):
    """商品絞り込み検索フォーム"""
    # --- (オプション) キーワード検索フィールド ---
    keyword = forms.CharField(
        label='キーワード',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '商品名、説明文、キーワードを入力', 'class': 'form-control'}),
    )

    # --- カテゴリ選択フィールド ---
    # 複数選択可能なチェックボックスとして表示
    category = forms.ModelMultipleChoiceField(
        label='カテゴリ',
        queryset=ProductCategory.objects.all().order_by('id'),
        widget=forms.CheckboxSelectMultiple,
        required=False, # 絞り込みなので必須ではない
    )

    # --- 価格帯指定フィールド ---
    price_min = forms.IntegerField(
        label='価格（下限）',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'placeholder': '例: 1000', 'class': 'form-control'}),
    )
    price_max = forms.IntegerField(
        label='価格（上限）',
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'placeholder': '例: 5000', 'class': 'form-control'}),
    )

    # --- サイズ選択フィールド ---
    # ProductモデルのSize Choicesを利用
    size = forms.TypedMultipleChoiceField(
        label='サイズ',
        choices=Product.Size.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        coerce=int, # 選択された値を整数に変換 (モデルの保存値が整数なので)
    )

    # --- 状態選択フィールド ---
    # ProductモデルのCondition Choicesを利用
    condition = forms.TypedMultipleChoiceField(
        label='商品の状態',
        choices=Product.Condition.choices, # Product.Condition の choices を利用
        widget=forms.CheckboxSelectMultiple,
        required=False,
        coerce=int, # 選択された値を整数に変換
    )

    def clean(self):
        """価格帯のバリデーション"""
        cleaned_data = super().clean()
        price_min = cleaned_data.get('price_min')
        price_max = cleaned_data.get('price_max')

        # 最小価格が最大価格を超えている場合
        if price_min is not None and price_max is not None and price_min > price_max:
            # 両方はくどいので片方にエラーメッセージを追加する
            self.add_error('price_min', '価格帯の指定が正しくありません。下限価格は上限価格以下にしてください。')
        return cleaned_data