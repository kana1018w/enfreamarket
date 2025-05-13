# interactions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from products.models import Product
from .models import Comment, Favorite, PurchaseIntent
from .forms import CommentForm

@login_required
@require_POST # POSTリクエストのみを受け付ける
def add_comment(request, product_pk):
    """商品にコメントを投稿する"""
    product = get_object_or_404(Product, pk=product_pk) # コメント対象の商品を取得
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.product = product         # コメントと商品を紐付ける
        comment.user = request.user       # コメントとユーザーを紐付ける
        comment.save()
        messages.success(request, 'コメントを投稿しました。')
    else:
        # コメント投稿は任意なのでエラーは発生しない
        # バリデーション追加した場合はここを修正
        for error_list in form.errors.values():
            for error in error_list:
                messages.error(request, error)
        # messages.error(request, 'コメントの投稿に失敗しました。入力内容を確認してください。')

    return redirect('products:product_detail', pk=product_pk)

@login_required
@require_POST # POSTリクエストのみを受け付ける
def favorite_toggle(request, product_pk):
    """お気に入り登録/解除"""
    product = get_object_or_404(Product, pk=product_pk)
    favorite, created = Favorite.objects.get_or_create(user=request.user, product=product) # created は新規作成時はTrue、既存のオブジェクトを取得時はFalse

    if created:
        messages.success(request, f'「{product.name}」をお気に入りに追加しました。')
    else:
        # レコードがすでに存在する　＝　お気に入り登録ずみでハートが押された　ので削除
        favorite.delete()
        messages.success(request, f'「{product.name}」をお気に入りから削除しました。')

    # リダイレクト先の決定
    # 各画面でnextパラメータを送るので基本的にはそれに準ずる
    # なかった場合は該当商品の商品詳細ページへリダイレクト
    default_redirect = reverse('products:product_detail', kwargs={'pk': product_pk})
    redirect_url = request.POST.get('next', default_redirect)

    # 'next' が空文字列だった場合や予期せぬ値の場合
    if not redirect_url:
        redirect_url = default_redirect

    return redirect(redirect_url)


@login_required
def favorite_list(request):
    """お気に入りした商品の一覧を表示する"""
    # Favorite オブジェクトのリストを取得
    favorites = Favorite.objects.filter(user=request.user).select_related(
        'product__main_product_image', # Productからメイン画像を参照する
    ).order_by('-created_at') # 新しくお気に入りしたものが上にくるように

    # お気に入り商品のステータスを表示するため、Product オブジェクトにステータスに応じたCSSクラスを追加
    for fav_item in favorites:
        if fav_item.product:
            product = fav_item.product # Productオブジェクトへのショートカット
            if product.status == Product.Status.FOR_SALE:
                product.status_class = "status-for-sale"
            elif product.status == Product.Status.IN_TRANSACTION:
                product.status_class = "status-in-transaction"
            elif product.status == Product.Status.SOLD:
                product.status_class = "status-sold"
            else:
                product.status_class = ""

    context = {
        'favorites': favorites, # Favoriteオブジェクトのリストを渡す
    }
    return render(request, 'interactions/favorite_list.html', context)


@login_required
@require_POST
def add_purchase_intent(request, product_pk):
    """商品に対する購入意思表示を作成する"""
    product = get_object_or_404(Product, pk=product_pk)

    # 自分が出品した商品には購入意思表示できない
    if product.user == request.user:
        messages.error(request, "ご自身が出品した商品には購入意思表示できません。")
        return redirect('products:detail', pk=product_pk)

    # 販売中の商品にしか購入意思表示できない
    if product.status != Product.Status.FOR_SALE:
        messages.error(request, "この商品は現在購入意思表示を受け付けていません。")
        return redirect('products:product_detail', pk=product_pk)

    # PurchaseIntentオブジェクトを作成 (get_or_create を使う)
    # 既に意思表示済みの場合、created は False になる
    intent, created = PurchaseIntent.objects.get_or_create(
        user=request.user,
        product=product
    )

    if created:
        messages.success(request, f'「{product.name}」への購入意思を伝えました。')
        # TODO: 出品者へのメール通知処理をここに追加

    else:
        # 既に意思表示済みの場合　（通りないはずだが）
        messages.info(request, f'「{product.name}」には既に購入意思表示をしています。')

    return redirect('products:product_detail', pk=product_pk)

@login_required
@require_POST
def delete_purchase_intent(request, product_pk):
    """商品に対する購入意思表示を取り消す"""
    product = get_object_or_404(Product, pk=product_pk)

    # ログインユーザーがこの商品に対して行った PurchaseIntent を取得
    try:
        intent = PurchaseIntent.objects.get(user=request.user, product=product)
    except PurchaseIntent.DoesNotExist:
        messages.error(request, "この商品に対するあなたの購入意思表示が見つかりません。")
        return redirect('products:product_detail', pk=product_pk)

    intent_product_name = intent.product.name # メッセージ用の商品名
    intent.delete()

    messages.success(request, f'「{intent_product_name}」への購入意思表示を取り消しました。')

    # リダイレクト先の決定
    # 各画面でnextパラメータを送るので基本的にはそれに準ずる
    # なかった場合は該当商品の商品詳細ページへリダイレクト
    default_redirect = reverse('products:product_detail', kwargs={'pk': product_pk})
    redirect_url = request.POST.get('next', default_redirect)

    # 'next' が空文字列だった場合や予期せぬ値の場合
    if not redirect_url:
        redirect_url = default_redirect

    return redirect(redirect_url)

@login_required
def sent_purchase_intents_list(request):
    """自分が行った購入意思表示の一覧を表示する"""
    # ログインユーザーが行った PurchaseIntent を取得
    sent_intents = PurchaseIntent.objects.filter(
        user=request.user # PurchaseIntent の user がログインユーザー
    ).select_related(
        'product',                     # PurchaseIntent -> Product
        'product__main_product_image'  # PurchaseIntent -> Product -> ProductImage
    ).order_by('-created_at')          # 新しい意思表示が上にくるように

    # ビューでステータスに応じてメッセージを表示する
    for intent in sent_intents:
        if intent.product:
            product = intent.product
            if product.status == Product.Status.FOR_SALE:
                product.status_class = "status-for-sale"
                product.status_message_display = "販売中"
            elif product.status == Product.Status.IN_TRANSACTION:
                product.status_class = "status-in-transaction"
                # 取引相手によってメッセージを変える
                if product.negotiating_user == request.user:
                    product.status_message_display = "取引中"
                else:
                    product.status_message_display = "他のユーザーと取引中"
            elif product.status == Product.Status.SOLD:
                product.status_class = "status-sold"
                if product.negotiating_user == request.user:
                    product.status_message_display = "購入済"
                else:
                    product.status_message_display = "他のユーザーに売却済"
            else:
                product.status_class = ""
                product.status_message_display = ""

    context = {
        'sent_intents': sent_intents,
    }
    return render(request, 'interactions/sent_purchase_intents_list.html', context)


@login_required
def received_purchase_intents_list(request):
    """購入意思表示を受けた商品の一覧"""
    # ログインユーザーが出品した商品に対する PurchaseIntent を取得
    # Product の user フィールドがログインユーザーである PurchaseIntent を絞り込む
    received_intents = PurchaseIntent.objects.filter(
        product__user=request.user
    ).select_related(
        'product',
        'user',
        'product__main_product_image'
    ).order_by('-created_at')

    context = {
        'received_intents': received_intents,
    }
    return render(request, 'interactions/received_purchase_intents_list.html', context)