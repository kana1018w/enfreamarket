# interactions/models.py
from django.db import models
from django.conf import settings # settings.AUTH_USER_MODEL を参照するため
from products.models import Product

class Favorite(models.Model):
    """お気に入りモデル"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, # ユーザー削除時にお気に入りも削除
        related_name='favorites',
        verbose_name='ユーザー'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE, # 商品削除時にお気に入りも削除
        related_name='favorited_by',
        verbose_name='商品'
    )
    created_at = models.DateTimeField('登録日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = 'お気に入り'
        verbose_name_plural = 'お気に入り'

        # 1人のユーザーは1つの商品に1回しかお気に入りできないように制約を追加
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_favorite')
        ]

    def __str__(self):
        return f'{self.user.display_name} : {self.product.name} をお気に入りに追加 ({self.created_at})'
    

class PurchaseIntent(models.Model):
    """購入意思表示モデル"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='purchase_intents',
        verbose_name='購入意思表示者'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='purchase_intended_by',
        verbose_name='商品'
    )
    
    created_at = models.DateTimeField('意思表示日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = '購入意思表示'
        verbose_name_plural = '購入意思表示'
        # 1人のユーザーは1つの商品に1回だけ購入意思表示できるように制約を追加 (必要に応じて)
        # もし複数回意思表示できる仕様なら、この制約は不要です。
        constraints = [
            models.UniqueConstraint(fields=['user', 'product'], name='unique_purchase_intent')
        ]

    def __str__(self):
        return f'{self.user.display_name} : {self.product.name} の購入意思表示 ({self.created_at})'


class Comment(models.Model):
    """商品コメントモデル"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='コメント投稿者'
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='商品'
    )
    content = models.TextField(
        verbose_name='コメント本文',
        blank=False, # 空のコメントは許可しない
        null=False   # DBレベルでもNULLを許可しない
    )
    created_at = models.DateTimeField('投稿日時', auto_now_add=True)
    updated_at = models.DateTimeField('更新日時', auto_now=True)

    class Meta:
        verbose_name = 'コメント'
        verbose_name_plural = 'コメント'
        ordering = ['created_at'] # 古いコメントから順に表示 (昇順)

    def __str__(self):
        return f'{self.product.name} - {self.user.display_name}: {self.text[:30]}...'