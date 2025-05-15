# interactions/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from products.models import Product
from .models import Comment, Favorite, PurchaseIntent
from .forms import CommentForm
from django.db import transaction
from django.template.loader import render_to_string
from django.conf import settings
from django.core.mail import send_mail

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

        if product.user != request.user: # 出品者とコメント投稿者が異なる場合のみ通知
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
                recipient_list = [product.user.email] # 出品者のメールアドレス

                send_mail(
                    subject,
                    message_body,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list,
                    fail_silently=False
                )
                print(f"New comment notification mail sent to {product.user.email} for product {product.name}") # 開発用
            except Exception as e:
                print(f"Error sending new comment notification email: {e}")
                messages.warning(request, "コメントは投稿しましたが、出品者への通知メールの送信に失敗しました。")
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
    ).order_by('-created_at') # 新しくお気に入りしたものが上にくるよう

    # 表示する各お気に入り商品に対して、購入意思表示状態を付与
    if request.user.is_authenticated: # ログインしている前提のページだが念のため
        # ログインユーザーが購入意思表示している商品IDのセットを取得
        purchase_intended_product_ids = set(
            PurchaseIntent.objects.filter(user=request.user).values_list('product_id', flat=True)
        )
        for fav_item in favorites:
            if fav_item.product: # productが存在することを確認
                product = fav_item.product

                # 購入意思表示状態を追加
                product.is_purchase_intended_by_current_user = product.pk in purchase_intended_product_ids

                # ステータスクラスとメッセージの設定
                product.status_message_info = ""
                if product.status == Product.Status.FOR_SALE:
                    product.status_class = "status-for-sale"
                    product.status_message_display = "販売中"
                elif product.status == Product.Status.IN_TRANSACTION:
                    product.status_class = "status-in-transaction"
                    product.status_message_display = "取引中"
                    if product.negotiating_user == request.user:
                        pass
                    elif product.negotiating_user:
                        product.status_message_info = "他のユーザーと取引中のため、購入意思表示は出来ません"
                elif product.status == Product.Status.SOLD:
                    product.status_class = "status-sold"
                    product.status_message_display = "売却済"
                    if product.negotiating_user == request.user:
                        pass
                    elif product.negotiating_user:
                        product.status_message_info = "他のユーザーに売却されました"
                else:
                    product.status_class = ""
                    product.status_message_display = ""

    context = {
        'favorites': favorites,
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
        # 出品者へのメール通知処理
        try:
            subject = f'【園フリマ】「{product.name}」に購入意思表示がありました'
            # メール本文をテンプレートから生成
            mail_context = {
                'user_display_name': request.user.display_name or request.user.get_username(), # 表示名がなければユーザー名
                'product_name': product.name,
                'received_intents_url': request.build_absolute_uri(
                    reverse('interactions:received_purchase_intents_list')
                ),
            }
            message_body = render_to_string('emails/purchase_intent_notification_email.txt', mail_context)
            recipient_list = [product.user.email] # 出品者のメールアドレス

            send_mail(
                subject,
                message_body,
                settings.DEFAULT_FROM_EMAIL,
                recipient_list,
                fail_silently=False # 送信失敗時にエラーを発生させる (開発中はTrueでも良い)
            )
            print(f"Mail sent to {product.user.email} for product {product.name}")
        except Exception as e:
            # メール送信失敗時のエラーハンドリング (ログ記録など)
            print(f"Error sending email for purchase intent: {e}")
            messages.warning(request, "購入意思は伝えましたが、出品者への通知メールの送信に失敗しました。")

    else:
        # 既に意思表示済みの場合　（通らないはずだが）
        messages.info(request, f'「{product.name}」には既に購入意思表示をしています。')

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
            product.status_message_info = "" # ステータスに応じた補助メッセージ
            if product.status == Product.Status.FOR_SALE:
                product.status_class = "status-for-sale"
                product.status_message_display = "販売中"
            elif product.status == Product.Status.IN_TRANSACTION:
                product.status_class = "status-in-transaction"
                if product.negotiating_user == request.user:
                    pass
                else:
                    product.status_message_info = "他のユーザーと取引中"
            elif product.status == Product.Status.SOLD:
                product.status_class = "status-sold"
                if product.negotiating_user == request.user:
                    pass
                else:
                    product.status_message_info = "他のユーザーに売却済"
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
    ).order_by('product__name', '-created_at')

    for intent in received_intents:
        if intent.product:
            product = intent.product
            product.status_message_info = "" # ステータスに応じた補助メッセージ
            if product.status == Product.Status.FOR_SALE:
                product.status_class = "status-for-sale"
                product.status_message_display = "販売中"
            elif product.status == Product.Status.IN_TRANSACTION:
                product.status_class = "status-in-transaction"
                product.status_message_display = "取引中" # ステータスバッジ用
                if product.negotiating_user == intent.user: # この意思表示者と取引中か
                    pass # 何も表示しない
                elif product.negotiating_user: # 他の誰かと取引中か
                    product.status_message_info = "他のユーザーと取引中"
                else: # negotiating_userがいないが取引中 (通常はありえないが念のため)
                    pass 
            elif product.status == Product.Status.SOLD:
                product.status_class = "status-sold"
                product.status_message_display = "売却済"
                if product.negotiating_user == intent.user: # この意思表示者に売却済か
                    pass
                elif product.negotiating_user:
                    product.status_message_info = "他のユーザーに売却済"
                else: # negotiating_userがいないが売却済
                    product.status_message_info = ""
            else:
                product.status_class = ""
                product.status_message_display = ""

    context = {
        'received_intents': received_intents,
    }
    return render(request, 'interactions/received_purchase_intents_list.html', context)


@login_required
@require_POST
def start_transaction(request, intent_pk):
    """購入意思表示に基づいて取引を開始ー"""
    # 対象の PurchaseIntent を取得
    intent = get_object_or_404(PurchaseIntent, pk=intent_pk)
    product = intent.product
    buyer = intent.user # 購入意思表示をしたユーザー

    # 権限チェック: ログインユーザーが商品の出品者であるか確認
    if product.user != request.user:
        messages.error(request, "この取引を開始する権限がありません。再度ログインしてください。")
        return redirect('accounts:login')

    # ステータスチェック: 商品が販売中であるか確認
    if product.status != Product.Status.FOR_SALE:
        messages.error(request, "この商品は既に取引中または売却済です。")
        return redirect('interactions:received_purchase_intents_list')

    try:
        with transaction.atomic(): # 複数のDB操作をまとめて実行
            # 1. 商品のステータスを「取引中」に更新
            product.status = Product.Status.IN_TRANSACTION
            # 2. 商品の取引相手 (negotiating_user) を設定
            product.negotiating_user = buyer
            product.save()

            # 3. 購入者にメールで通知
            try:
                subject = f'【園フリマ】「{product.name}」の取引が開始されました'
                mail_context = {
                    'buyer_display_name': buyer.display_name or buyer.get_username(),
                    'product_name': product.name,
                    'product_detail_url': request.build_absolute_uri(
                        reverse('products:product_detail', kwargs={'pk': product.pk})
                    ),
                }
                message_body = render_to_string('emails/transaction_started_email.txt', mail_context)
                recipient_list = [buyer.email] # 購入者のメールアドレス

                send_mail(
                    subject,
                    message_body,
                    settings.DEFAULT_FROM_EMAIL,
                    recipient_list,
                    fail_silently=False
                )
                print(f"Transaction started mail sent to {buyer.email} for product {product.name}") # 開発用
            except Exception as e:
                print(f"Error sending transaction started email: {e}")
                messages.warning(request, "取引は開始しましたが、購入者への通知メールの送信に失敗しました。")

            messages.success(request, f"「{product.name}」について、{buyer.display_name}さんとの取引を開始しました。")

    except Exception as e:
        messages.error(request, f"取引開始処理中にエラーが発生しました: {e}")
        # エラーログなども記録すると良い
        print(f"Error during start_transaction: {e}")

    return redirect('interactions:received_purchase_intents_list')


@login_required
@require_POST
def complete_transaction(request, intent_pk):
    """購入意思表示に基づいて取引を完了"""
    # 対象の PurchaseIntent を取得
    intent = get_object_or_404(PurchaseIntent, pk=intent_pk)
    product = intent.product
    buyer = intent.user

    # 権限チェック: ログインユーザーが商品の出品者であるか確認
    if product.user != request.user:
        messages.error(request, "この取引を完了する権限がありません。再度ログインしてください。")
        return redirect('accounts:login')

    # ステータスチェック: 商品が「取引中」であり、かつ取引相手が正しいか確認
    if not (product.status == Product.Status.IN_TRANSACTION and product.negotiating_user == buyer):
        messages.error(request, "この取引は現在完了できる状態ではありません。")
        return redirect('interactions:received_purchase_intents_list')

    try:
        with transaction.atomic():
            # 1. 商品のステータスを「売却済」に更新
            product.status = Product.Status.SOLD
            # product.negotiating_user はそのまま (誰と取引したかの記録)
            product.save()

            # TODO: 2. 購入者と出品者にメールで通知 (次のステップで実装)

            messages.success(request, f"「{product.name}」の {buyer.display_name}さんとの取引を完了しました。")

    except Exception as e:
        messages.error(request, f"取引完了処理中にエラーが発生しました: {e}")
        print(f"Error during complete_transaction: {e}")

    return redirect('interactions:received_purchase_intents_list')