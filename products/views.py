from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from .forms import ProductForm
from .models import Product, ProductImage
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import PermissionDenied


# Create your views here.
def index(request):
    return render(request, 'products/index.html')

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
def detail(request, pk):
    return render(request, 'products/detail.html')

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

# 気になるリスト
def favorite_list(request): 
    return render(request, 'products/favorite_list.html')

# ご利用規約
def terms(request):
    return render(request, 'products/terms.html')