from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from .forms import SignUpForm, EmailAuthenticationForm, NameChangeForm, DisplayNameChangeForm, EmailChangeForm, CustomPasswordChangeForm
from .models import User
from django.contrib.auth import login as auth_login, logout as auth_logout, update_session_auth_hash 
from django.contrib import messages # メッセージを表示する場合に使う
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin
from products.models import Product, ProductImage







# Create your views here.
def login(request):
    """
    ログインビュー
    """
    # ログイン済みユーザーがアクセスしたらトップページへリダイレクト (任意)
    if request.user.is_authenticated:
        return redirect('products:top') # トップページのURL名

    if request.method == 'POST':
        # カスタマイズした EmailAuthenticationForm を使用
        form = EmailAuthenticationForm(request, data=request.POST)
        if form.is_valid():
            # 認証成功
            # form.get_user() で認証されたユーザーオブジェクトを取得
            user = form.get_user()
            # ログイン状態にする
            auth_login(request, user)
            messages.success(request, f'ようこそ{user.display_name or user.name}さん、ログインしました。')
            return redirect('products:top')
        # else: バリデーション失敗 -> エラー付きフォームが render される
    else:
        # GETリクエスト -> 空のフォームを表示
        form = EmailAuthenticationForm()

    context = {'form': form}
    return render(request, 'accounts/login.html', context)

@login_required
def logout(request):
    """
    ログアウトビュー
    """
    # POSTリクエストのみ受け付ける (CSRF対策のため推奨)
    if request.method == 'POST':
        auth_logout(request)
        messages.info(request, 'ログアウトしました。')
        return redirect('accounts:login')
    else:
        return redirect('products:top')

def signup(request):
    """
    アカウント新規登録ビュー
    """
    if request.method == 'POST':
        # 送信されたデータ (request.POST) を使ってフォームをインスタンス化
        form = SignUpForm(request.POST)

        # フォームのバリデーションを実行 (.is_valid() を呼ぶと、forms.pyのcleanメソッドなどが実行される)
        if form.is_valid():
            # バリデーション成功！ cleaned_data に検証済みのデータが入っている
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            name = form.cleaned_data['name']
            display_name = form.cleaned_data.get('display_name') # 任意入力なので .get() を使う
            kindergarten = form.cleaned_data['kindergarten']

            try:
                # User.objects (CustomUserManager) の create_user メソッドを呼び出してユーザーを作成
                # ※ forms.py でバリデーション済みなので、基本的にはここでエラーは起きにくい想定
                user = User.objects.create_user(
                    email=email,
                    password=password, # create_user内でハッシュ化される
                    name=name,
                    kindergarten=kindergarten,
                    display_name=display_name # display_nameも渡す
                )

                # 登録成功後の処理 
                auth_login(request, user)

                messages.success(request, 'アカウント登録が完了しました。ご利用のルールをご確認の上、サービスをご利用ください。')
                return redirect('products:top')

            except ValueError as e:
                # models.py の create_user 内で発生した ValueError をキャッチした場合
                # (例: 万が一、フォームでチェックしきれなかった必須項目漏れなど)
                form.add_error(None, f"登録エラーが発生しました: {e}") # フォーム全体のエラーとして表示
            except Exception as e:
                # その他の予期せぬエラーが発生した場合
                print(f"予期せぬエラー: {e}") # 開発中はコンソールに出力
                form.add_error(None, '登録中に予期せぬエラーが発生しました。しばらくしてから再度お試しください。')

        else:
            # フォームが無効な場合 (バリデーションNG)
            messages.error(request, '入力内容に誤りがあります。内容を確認してください。')

    # GETリクエストの場合 (最初にページを開いた場合)
    else:
        form = SignUpForm()

    # GETリクエストの場合、またはPOSTでバリデーション失敗した場合に実行される
    # テンプレートにフォームオブジェクトを渡してレンダリング
    context = {
        'form': form,
    }
    return render(request, 'accounts/signup.html', context)

@login_required
def mypage(request):
    """
    マイページ表示ビュー
    """
    # ログイン中のユーザーオブジェクトは request.user で取得できる
    user = request.user

    # テンプレートに渡すデータ (コンテキスト) を作成
    context = {
        'user': user,
    }

    return render(request, 'accounts/mypage.html', context)


@login_required
def my_listings(request):
    """出品した商品一覧ビュー"""
    # ログイン中のユーザーが出品した商品を取得
    # Productモデルの user フィールドでフィルター
    # main_product_image を参照するので select_related でJoinした結果を取得しておく (N+1対策)
    user_products = Product.objects.filter(user=request.user).select_related(
        'main_product_image' # メイン画像の情報を一緒に取得
    ).order_by('-created_at')

    # 商品のステータスに応じてステータスクラスを追加し、テンプレートに渡す
    for product in user_products:
        if product.status == Product.Status.FOR_SALE:
            product.status_class = "status-for-sale"
        elif product.status == Product.Status.IN_TRANSACTION:
            product.status_class = "status-in-transaction"
        elif product.status == Product.Status.SOLD:
            product.status_class = "status-sold"
        else:
            product.status_class = ""

    context = {
        'products': user_products,
    }
    return render(request, 'accounts/my_listings.html', context)

@login_required
def my_intents_given(request):
    return render(request, 'accounts/my_intents_given.html')
@login_required
def my_intents_received(request):
    return render(request, 'accounts/my_intents_received.html')

@login_required
def profile_name_edit(request):
    """
    名前変更ビュー
    """
    # 更新対象のユーザーはリクエストから取得
    user = request.user

    if request.method == 'POST':
        # POSTリクエストの場合: 送信されたデータと、更新対象のユーザーインスタンスでフォームを初期化
        form = NameChangeForm(request.POST, instance=user)
        if form.is_valid():
            # バリデーション成功: フォームの変更をデータベースに保存
            form.save()
            messages.success(request, '名前を変更しました。')
            # 変更後はマイページなどにリダイレクト
            return redirect('accounts:mypage') # マイページのURL名
        # else: バリデーション失敗 -> エラー付きフォームが render される
    else:
        form = NameChangeForm(instance=user)

    # GETリクエスト、またはPOSTでバリデーション失敗した場合に実行
    context = {
        'form': form,
    }
    # 名前変更用のテンプレートをレンダリング
    return render(request, 'accounts/name_edit.html', context)

@login_required
def profile_display_name_edit(request):
    """
    表示名変更ビュー
    """
    # 更新対象のユーザーはリクエストから取得
    user = request.user

    if request.method == 'POST':
        # POSTリクエストの場合: 送信されたデータと、更新対象のユーザーインスタンスでフォームを初期化
        form = DisplayNameChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, '表示名を変更しました。')
            # 変更後はマイページなどにリダイレクト
            return redirect('accounts:mypage') # マイページのURL名
        # else: バリデーション失敗 -> エラー付きフォームが render される
    else:
        form = DisplayNameChangeForm(instance=user)

    context = {
        'form': form,
    }

    return render(request, 'accounts/display_name_edit.html', context)

@login_required
def profile_email_edit(request):
    """
    メールアドレス変更ビュー
    """
    user = request.user
    if request.method == 'POST':
        form = EmailChangeForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'メールアドレスを変更しました。')
            return redirect('accounts:mypage')
    else:
        form = EmailChangeForm(instance=user)

    context = {
        'form': form,
    }

    return render(request, 'accounts/email_edit.html', context)


class ProfilePasswordEditView(LoginRequiredMixin, PasswordChangeView): # ← クラスとして定義し、継承する
    """パスワード変更ビュー"""
    # クラス属性として定義
    form_class = CustomPasswordChangeForm
    template_name = 'accounts/password_edit.html'
    success_url = reverse_lazy('accounts:mypage')

    # メソッドとして定義
    def form_valid(self, form):
        # 親クラスの form_valid を呼び出す前にメッセージを設定することも可能
        messages.success(self.request, 'パスワードを変更しました。')
        # パスワード変更後にセッションを維持
        update_session_auth_hash(self.request, form.user)
        # 親クラスの form_valid を呼び出してリダイレクト処理などを行わせる
        return super().form_valid(form)
