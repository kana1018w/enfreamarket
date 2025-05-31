from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import Q
from .forms import ProductForm, ProductSearchForm
from .models import Product, ProductImage
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from interactions.models import Comment, Favorite, PurchaseIntent
from interactions.forms import CommentForm
from django.urls import reverse
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail

import logging
logger = logging.getLogger(__name__)

@login_required
def product_list_view(request):
    """トップページ (商品一覧) ビュー"""
    # 1. 商品データの取得とフィルタリング
    # ログインユーザーの所属園を取得
    user_kindergarten = None
    if request.user.is_authenticated and hasattr(request.user, 'kindergarten') and request.user.kindergarten:
        user_kindergarten = request.user.kindergarten
    else:
        messages.error(request, "所属園の情報が取得できませんでした。ログインし直してください。")
        return redirect('accounts:login')

    queryset = Product.objects.filter(status=Product.Status.FOR_SALE, kindergarten=user_kindergarten)

    if request.user.is_authenticated:
        queryset = queryset.exclude(user=request.user) # 自分が出品したものを除外

    queryset = queryset.select_related(
        'main_product_image',
        'product_category'
    ).order_by('-created_at')

    # 検索結果を表示しない時用に変数の初期化
    selected_category_for_breadcrumb_obj = None

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
                selected_category_for_breadcrumb_obj = categories.first() # 最初のカテゴリオブジェクト

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

    # ページ上の商品に対し、お気に入り状態を追加
    products_for_page = list(queryset.select_related('main_product_image', 'product_category').order_by('-created_at'))

    if request.user.is_authenticated:
        # 現在のログインユーザーがお気に入り登録している全ての商品IDのセット
        # 1. お気に入り登録済みの商品IDを取得, flat=True で値（product_id）が直接入ったリストを返す
        # 2. set() で重複を取り除く
        favorited_product_ids = set(
            Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
        # 3.現在の商品のID (product.pk) が、取得したお気に入り商品IDのセット (favorited_product_ids) の中に含まれているかどうかを判定
        # 含まれていれば True, 含まれていなければ False
        for product in products_for_page:
            product.is_favorited_by_current_user = product.pk in favorited_product_ids
    else:
        for product in products_for_page:
            product.is_favorited_by_current_user = False

    # 3. ページネーション処理
    paginator = Paginator(products_for_page, 10) # 1ページあたり10件表示
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
        'selected_category_for_breadcrumb_obj': selected_category_for_breadcrumb_obj, # パンクズリストのカテゴリ表示で使用
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
                uploaded_sub_image_1 = form.cleaned_data.get('sub_image_1')
                if uploaded_sub_image_1:
                    ProductImage.objects.create(
                        product=product,
                        image=uploaded_sub_image_1,
                        display_order=1
                    )

                uploaded_sub_image_2 = form.cleaned_data.get('sub_image_2')
                if uploaded_sub_image_2:
                    ProductImage.objects.create(
                        product=product,
                        image=uploaded_sub_image_2,
                        display_order=2
                    )

                uploaded_sub_image_3 = form.cleaned_data.get('sub_image_3')
                if uploaded_sub_image_3:
                    ProductImage.objects.create(
                        product=product,
                        image=uploaded_sub_image_3,
                        display_order=3
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

    
    # ログインユーザーが出品者かどうかを判定するフラグ
    is_owner = False
    if request.user.is_authenticated and product.user == request.user:
        is_owner = True

    # ログインユーザーがお気に入りしたかどうかを判定するフラグ
    is_favorited = False
    if request.user.is_authenticated:
        is_favorited = Favorite.objects.filter(user=request.user, product=product).exists()

    # 購入意思表示状態の判定
    is_purchase_intended = False
    if request.user.is_authenticated:
        is_purchase_intended = PurchaseIntent.objects.filter(user=request.user, product=product).exists()

    # 関連するコメントを取得
    comments = product.comments.all().order_by('created_at') # 関連するコメントを取得し、古い順に並べる
 
    # コメントフォーム処理
    if request.method == 'POST':
        # コメント投稿処理
        comment_form_data = CommentForm(request.POST)
        if comment_form_data.is_valid():
            comment = comment_form_data.save(commit=False)
            comment.product = product
            comment.user = request.user
            comment.save()
            messages.success(request, 'コメントを投稿しました。')

            # メール通知処理
            if product.user != request.user:
                try:
                    subject = f'【園フリマ】「{product.name}」に新しいコメントがありました'
                    mail_context = {
                        'product_owner_display_name': product.user.display_name or product.user.get_username(),
                        'product_name': product.name,
                        'commenter_display_name': request.user.display_name or request.user.get_username(),
                        'comment_text': comment.content,
                        'product_detail_url': request.build_absolute_uri(
                            reverse('products:product_detail', kwargs={'pk': product.pk})
                        ),
                    }
                    message_body = render_to_string('emails/new_comment_notification_email.txt', mail_context)
                    recipient_list = [product.user.email]

                    send_mail(
                        subject,
                        message_body,
                        settings.DEFAULT_FROM_EMAIL,
                        recipient_list,
                        fail_silently=False
                    )
                    logger.info(
                        f"Successfully new comment notification email. "
                        f"Product: {product.name} (ID: {product.pk}), "
                        f"Send to: {product.user.email},"
                        f"Comment: {comment.content},"
                        # 出品者情報
                        f"Product Owner: {product.user.display_name} ({product.user.email}), "
                        # コメント者情報
                        f"Commenter: {request.user.display_name} ({request.user.email}), "
                    )
                except Exception as e:
                    print(f"Error sending new comment notification email: {e}")
                    logger.error(
                        f"[[MAIL ERROR]] Failed to send new comment notification email. "
                        f"Product: {product.name} (ID: {product.pk}), "
                        f"Send to: {product.user.email}"
                        f"Comment: {comment.content},"
                        f"Product Owner: {product.user.display_name} ({product.user.email}), "
                        f"Commenter: {request.user.display_name} ({request.user.email}), "
                        f"Error: {e}",
                        exc_info=True
                    )
                    messages.warning(request, "コメントは投稿しましたが、出品者への通知メールの送信に失敗しました。")

            return redirect('products:product_detail', pk=product.pk) # 成功時はリダイレクト
        else:
            # エラーメッセージを表示
            comment_form = comment_form_data
    else:
        # GETリクエストの場合、空のフォームを準備
        comment_form = CommentForm()

    context = {
        'product': product,
        'sub_images': sub_images,
        'is_owner': is_owner,
        'is_purchase_intended': is_purchase_intended,
        'is_favorited': is_favorited,
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
        form = ProductForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            try:
                with transaction.atomic():
                    # テキストベースのフィールドを保存
                    updated_product = form.save(commit=False) # まだDBには保存しない

                    # メイン画像の更新処理
                    new_main_image_file = form.cleaned_data.get('main_image') # フォームから新しい画像ファイルを取得

                    if new_main_image_file: # 新しい画像がアップロードされた場合
                        # 1. 既存のメイン画像を削除
                        if product.main_product_image:
                            print(f"Debug: Existing main image (ID: {product.main_product_image.pk}) will be deleted.")
                            # まずファイルシステムから画像ファイルを削除
                            product.main_product_image.image.delete(save=False) # save=False でDB更新はしない
                            # 次に ProductImage レコードを削除
                            product.main_product_image.delete()
                            updated_product.main_product_image = None # 一旦Noneにしておく

                        # 2. 新しい ProductImage を作成して紐付ける
                        new_pi = ProductImage.objects.create(
                            product=updated_product, # この時点ではまだ updated_product は保存されていないが、後で保存される
                            image=new_main_image_file,
                            display_order=0
                        )
                        updated_product.main_product_image = new_pi

                    # サブ画像の更新処理
                    existing_sub_images_map = product.get_sub_images_as_dict()
                    for i in range(1, 4): # 1, 2, 3
                        new_sub_image_file = form.cleaned_data.get(f'sub_image_{i}') # フォームから新しい画像ファイルを取得 (1, 2, 3)
                        current_sub_image_instance = existing_sub_images_map.get(i)

                        if new_sub_image_file: # 新しい画像がアップロードされた場合
                            if current_sub_image_instance:
                                # 既存のサブ画像を削除
                                current_sub_image_instance.image.delete(save=False)
                                # 既存のサブ画像を更新
                                current_sub_image_instance.image = new_sub_image_file
                                current_sub_image_instance.save()
                            else:
                                # 新しいサブ画像を作成
                                ProductImage.objects.create(
                                    product=updated_product, # この時点ではまだ updated_product は保存されていないが、後で保存される
                                    image=new_sub_image_file,
                                    display_order=i
                                )    

                    # 全ての変更をDBに保存
                    updated_product.save()

                messages.success(request, '商品情報を更新しました。')
                return redirect('accounts:my_listings')

            except Exception as e:
                print(f"Error during product update (text fields only): {e}")
                messages.error(request, '商品情報の更新中にエラーが発生しました。')
                # エラー発生時もフォームを再表示 (編集中のデータを保持)
                context = {
                    'form': form,
                    'product': product, # テンプレートで商品情報を参照する場合に備えて渡す
                    'sub_images_map': product.get_sub_images_as_dict(),
                }
                return render(request, 'products/edit.html', context)

        else:
            print(form.errors)
            messages.error(request, '入力内容に誤りがあります。ご確認ください。')
            # エラーメッセージ付きのフォームを再表示
            context = {
                'form': form,
                'product': product,
                'sub_images_map': product.get_sub_images_as_dict(),
            }
            return render(request, 'products/edit.html', context)

    else:
        # GETリクエストの場合
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'sub_images_map': product.get_sub_images_as_dict(),
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