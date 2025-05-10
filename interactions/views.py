# interactions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from products.models import Product
from .models import Comment
from .forms import CommentForm

@login_required
@require_POST # このビューはPOSTリクエストのみを受け付ける
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