from django.db import models
from .choices import PREFECTURES

# 幼稚園モデル
class Kindergarten(models.Model):
        name = models.CharField('園名',max_length=100,help_text='幼稚園の正式名称を入力してください。')
        auth_code = models.CharField('認証コード',max_length=50,unique=True,help_text='ユーザー登録時に使用する一意のコードです。')
        zip_code = models.CharField('郵便番号',max_length=8, help_text='ハイフン付きで入力してください (例: 123-4567)。')
        prefecture = models.CharField('都道府県',max_length=10,choices=PREFECTURES,default='',help_text='都道府県名を入力してください。')
        address = models.CharField('住所',max_length=255, help_text='都道府県以降の住所を入力してください。')# 市区町村、番地、建物名など
        created_at = models.DateTimeField('登録日時',auto_now_add=True)
        updated_at = models.DateTimeField('更新日時',auto_now=True)
        def __str__(self):
            return self.name
        
        class Meta:
            verbose_name = '幼稚園' # 管理画面でのモデル名の単数形  
            verbose_name_plural = '幼稚園一覧' # 管理画面でのモデル名の複数形
    