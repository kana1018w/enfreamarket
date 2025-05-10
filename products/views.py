from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Q
from .forms import ProductForm, ProductSearchForm
from .models import Product, ProductImage
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from interactions.models import Comment
from interactions.forms import CommentForm

def product_list_view(request): # 関数名を変更 (例: top_view, product_list_view などでも可)
    """トップページ (商品一覧) ビュー"""

    # 1. 商品データの取得とフィルタリング
    # Product.Status.ON_SALE の値はモデル定義に合わせてください。
    queryset = Product.objects.filter(status=Product.Status.FOR_SALE).select_related(
        'main_product_image',
        'product_category'
    ).order_by('-created_at')

    # 検索結果を表示しない時用に変数の初期化
    selected_category_for_breadcrumb = None

    # 2. 検索フォームの処理
    search_form = ProductSearchForm(request.GET or None)

    if search_form.is_valid():
        # 検索ルール
        # キーワード、カテゴリ、価格、の絞り込みは AND 検索で行う
        # サイズ、状態の絞り込みは OR 検索で行う　（チェックされたサイズ（状態）のいずれかに合致する）
        
        # --- キーワード検索 ---
        keyword = search_form.cleaned_data.get('keyword')
        if keyword:
            # 商品名 (name) または 商品説明 (description) にキーワードが含まれるものをOR検索
            # 大文字・小文字を区別しない部分一致 (icontains)
            queryset = queryset.filter(
                Q(name__icontains=keyword) | Q(description__icontains=keyword)
            )

        # --- カテゴリ絞り込み ---
        categories = search_form.cleaned_data.get('category') # ModelMultipleChoiceFieldはクエリセットを返す
        if categories: # 何かカテゴリが選択されていれば
            queryset = queryset.filter(product_category__in=categories)
            if categories.exists(): # 選択されたカテゴリが1つ以上あれば
                selected_category_for_breadcrumb = categories.first().name # 最初のカテゴリ名

        # --- 価格帯絞り込み ---
        price_min = search_form.cleaned_data.get('price_min')
        if price_min is not None: # 0も有効な値なので is not None でチェック
            queryset = queryset.filter(price__gte=price_min)

        price_max = search_form.cleaned_data.get('price_max')
        if price_max is not None:
            queryset = queryset.filter(price__lte=price_max)

        # --- サイズ絞り込み ---
        sizes = search_form.cleaned_data.get('size')
        if sizes:
            query_size = Q()
            for s in sizes:
                query_size |= Q(size=s) # 各サイズに対してOR条件でつなぐ
            if query_size: # 何かサイズが選択されていれば
                 queryset = queryset.filter(query_size)

        # --- 状態絞り込み ---
        conditions = search_form.cleaned_data.get('condition')
        if conditions:
            query_condition = Q()
            for c in conditions:
                query_condition |= Q(condition=c)
            if query_condition:
                 queryset = queryset.filter(query_condition)

    # else:
        # フォームが無効な場合 (例: price_min > price_max)、エラーはフォームオブジェクトに
        # 格納されているので、テンプレート側で表示できる。
        # クエリセットは初期状態のまま (フィルタリングしない)。
        # print(search_form.errors) # デバッグ用にエラー表示

    # 3. ページネーション処理
    paginator = Paginator(queryset, 10) # 1ページあたり10件表示
    page_number = request.GET.get('page')

    try:
        products_on_page = paginator.page(page_number)
    except PageNotAnInteger:
        # 'page' パラメータが整数でない場合、最初のページを表示
        products_on_page = paginator.page(1)
    except EmptyPage:
        # 'page' パラメータが範囲外の場合 (例: 9999ページ目)、最後のページを表示
        products_on_page = paginator.page(paginator.num_pages)

    context = {
        'products': products_on_page, # 現在のページの商品リスト
        'search_form': search_form,   # 絞り込み検索フォーム (後で追加)
        'selected_category_for_breadcrumb': selected_category_for_breadcrumb, # パンクズリストのカテゴリ表示で使用
    }
    return render(request, 'products/product_list.html', context)

# 商品出品
@login_required # ログイン必須にするデコレータ
def sell(request):
    """商品出品ビュー"""
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # 1. Product オブジェクトを準備 (まだDBには保存しない)
                product = form.save(commit=False)

                # 2. 出品者と所属園をログインユーザー情報から設定
                product.user = request.user
                # request.user に kindergarten 属性がある想定 (カスタムユーザーモデル)
                if hasattr(request.user, 'kindergarten'):
                    product.kindergarten = request.user.kindergarten
                else:
                    # kindergarten 属性がない場合ログイン画面へリダイレクト(エラーにするか、Noneを許容するかなど)
                    messages.error(request, "ユーザー情報に所属園が設定されていません。再度ログインしてください。")
                    return redirect('accounts:login')

                # 3. ステータスを「販売中」に設定
                product.status = Product.Status.FOR_SALE

                # 4. Product オブジェクトをDBに保存 (ここで初めてIDが割り振られる)
                product.save()

                # --- 画像処理 ---
                # 5. メイン画像を ProductImage として保存し、Product に紐付ける
                main_image_saved = False # メイン画像が保存されたか追跡するフラグ
                main_image_file = form.cleaned_data.get('main_image')
                if main_image_file:
                    main_pi = ProductImage.objects.create(
                        product=product,
                        image=main_image_file,
                        display_order=0 # メイン画像は display_order=0
                    )
                    # 作成した ProductImage を Product の main_product_image フィールドに設定
                    product.main_product_image = main_pi
                    # main_product_image フィールドのみを更新
                    product.save(update_fields=['main_product_image'])
                    main_image_saved = True

                if not main_image_saved:
                    raise ValueError("メイン画像の保存に失敗しました。")

                # 6. サブ画像を ProductImage として保存
                sub_image_files = form.cleaned_data.get('sub_images')
                if sub_image_files:
                    for i, sub_image_file in enumerate(sub_image_files, start=1):
                        # display_order を 1, 2, 3,... と設定
                        if i <= 3: # 最大3枚まで formでチェック済みだが、念のため
                            ProductImage.objects.create(
                                product=product,
                                image=sub_image_file,
                                display_order=i
                            )

                # 7. 成功メッセージを設定
                messages.success(request, '商品を出品しました。')

                # 8. 出品した商品 へリダイレクト
                return redirect('accounts:my_listings')

            except ValueError as e:
                form.add_error(None, f"登録エラーが発生しました: {e}") # フォーム全体のエラーとして表示

            except Exception as e:
                print(f"予期せぬエラー: {e}")
                form.add_error(None, '登録中に予期せぬエラーが発生しました。しばらくしてから再度お試しください。')

        else:
            # フォームが無効な場合 (バリデーションNG)
            messages.error(request, '入力内容に誤りがあります。内容を確認してください。')

    else:
        # GETリクエストの場合: 空のフォームを表示
        form = ProductForm()

    context = {'form': form}
    return render(request, 'products/sell.html', context)

# 商品詳細
@login_required
def detail(request, pk):
    """商品詳細ページビュー"""
    # Product オブジェクトを取得。関連オブジェクトも効率的に取得
    # select_related: ForeignKey または OneToOneField (単一オブジェクト)
    # prefetch_related: ManyToManyField または Reverse ForeignKey (複数オブジェクト)
    product = get_object_or_404(
        Product.objects.select_related(
            'user__kindergarten',
            'product_category',
            'main_product_image'
        ).prefetch_related(
            'images', # ProductImage を逆参照 (related_name='images')
            'comments__user' # Comment を逆参照 (related_name='comments') 
        ),
        pk=pk
    )
    sub_images = product.images.filter(display_order__gt=0).order_by('display_order')

    
    # 関連するコメントを取得
    comments = product.comments.all().order_by('created_at') # 関連するコメントを取得し、古い順に並べる
    comment_form = CommentForm()

    # ログインユーザーが出品者かどうかを判定するフラグ
    is_owner = False
    if request.user.is_authenticated and product.user == request.user:
        is_owner = True

    context = {
        'product': product,
        'is_owner': is_owner,
        'sub_images': sub_images,
        'comments': comments,
        'comment_form': comment_form,
    }

    return render(request, 'products/detail.html', context)

# 商品編集
@login_required
def edit(request, pk):
    """商品編集ビュー (一旦画像編集機能を除く)"""
    product = get_object_or_404(Product, pk=pk)

    if product.user != request.user:
        messages.error(request, "この商品を編集する権限がありません。ログインし直してください。")
        return redirect('accounts:login')

    if request.method == 'POST':
        # 編集データを取得
        form = ProductForm(request.POST, instance=product)

        if form.is_valid():
            try:
                # 複数のフィールド更新のため、トランザクションを開始
                with transaction.atomic():
                    form.save()

                messages.success(request, '商品情報を更新しました。')
                return redirect('accounts:my_listings')

            except Exception as e:
                print(f"Error during product update (text fields only): {e}")
                messages.error(request, '商品情報の更新中にエラーが発生しました。')
                # エラー発生時もフォームを再表示 (編集中のデータを保持)
                context = {
                    'form': form,
                    'product': product # テンプレートで商品情報を参照する場合に備えて渡す
                }
                return render(request, 'products/edit.html', context)

        else:
            print(form.errors)
            messages.error(request, '入力内容に誤りがあります。ご確認ください。')
            # エラーメッセージ付きのフォームを再表示
            context = {
                'form': form,
                'product': product
            }
            return render(request, 'products/edit.html', context)

    else:
        # GETリクエストの場合
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product
    }
    return render(request, 'products/edit.html', context)


# 商品削除
@login_required
def delete(request, pk):
    """商品削除 (確認画面表示 & 削除実行)"""
    product = get_object_or_404(Product, pk=pk)
    sub_images = product.images.filter(display_order__gt=0)

    # 出品者でなければ削除できない
    if product.user != request.user:
        messages.error(request, "この商品を削除する権限がありません。ログインし直してください。")
        return redirect('accounts:login')

    if request.method == 'POST':
        try:
            # 既存のメイン画像を削除
            if product.main_product_image:
                product.main_product_image.image.delete(save=False) # ファイル削除
                product.main_product_image.delete() # ProductImageレコード削除

            # 既存のサブ画像を削除 とファイル)
            for sub_image in sub_images:
                sub_image.image.delete(save=False)
                sub_image.delete()

            product.delete() # 商品オブジェクト自体を削除
            messages.success(request, f'商品「{product.name}」を削除しました。')
            return redirect('accounts:my_listings')
        except Exception as e:
            messages.error(request, '商品の削除中にエラーが発生しました。')
            # エラー時は商品詳細ページなどに戻すか、再度確認画面を表示
            return redirect('products:edit', pk=product.pk)

    # GETリクエストの場合 (最初に削除ボタンが押された時、または削除確認画面の再表示)
    context = {
        'product': product
    }
    return render(request, 'products/delete_confirm.html', context)


# 気になるリスト
def favorite_list(request): 
    return render(request, 'products/favorite_list.html')

# ご利用規約
def terms(request):
    return render(request, 'products/terms.html')