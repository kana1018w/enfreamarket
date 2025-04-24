from django.shortcuts import render, redirect
from .forms import SignUpForm, EmailAuthenticationForm
from .models import User
from django.contrib.auth import login as auth_login # 登録後に自動ログインさせる場合に使う (任意)
from django.contrib.auth import logout as auth_logout
from django.contrib import messages # メッセージを表示する場合に使う
from django.contrib.auth.decorators import login_required




# Create your views here.
def login(request):
    """
    ログインビュー
    """
    # ログイン済みユーザーがアクセスしたらトップページへリダイレクト (任意)
    if request.user.is_authenticated:
        return redirect('freamarket:index') # トップページのURL名

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
            return redirect('freamarket:index') # トップページのURL名
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
        return redirect('freamarket:index')

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

                # このメッセージは、リダイレクト先のテンプレートで表示できます。
                messages.success(request, 'アカウント登録が完了しました。ご利用のルールをご確認の上、サービスをご利用ください。')
                return redirect('freamarket:index')

            except ValueError as e:
                # models.py の create_user 内で発生した ValueError をキャッチした場合
                # (例: 万が一、フォームでチェックしきれなかった必須項目漏れなど)
                form.add_error(None, f"登録エラーが発生しました: {e}") # フォーム全体のエラーとして表示
            except Exception as e:
                # その他の予期せぬエラーが発生した場合
                # (実際には、エラー内容をログに記録するなどの処理が推奨されます)
                print(f"予期せぬエラー: {e}") # 開発中はコンソールに出力
                form.add_error(None, '登録中に予期せぬエラーが発生しました。しばらくしてから再度お試しください。')

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
    return render(request, 'accounts/my_listings.html')

@login_required
def my_intents_given(request):
    return render(request, 'accounts/my_intents_given.html')
@login_required
def my_intents_received(request):
    return render(request, 'accounts/my_intents_received.html')

@login_required
def profile_edit(request):
    return render(request, 'accounts/profile_edit.html')

@login_required
def password_change(request):
    return render(request, 'accounts/password_change.html')
