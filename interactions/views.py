# interactions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from products.models import Product
from .models import Comment, Favorite
from .forms import CommentForm

@login_required
@require_POST # POSTリクエストのみを受け付ける
def add_comment(request, product_pk):
    """商品にコメントを投稿するビュー"""
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
    """お気に入り登録/解除ビュー"""
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
    """お気に入りした商品の一覧を表示するビュー"""
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