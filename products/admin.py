from django.contrib import admin
from .models import ProductCategory, Product, ProductImage


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name',)
    list_editable = ('name',) # 一覧画面で直接編集できるようにする


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'status' , 'created_at', 'updated_at')
    search_fields = ('name', 'status')
    list_editable = ('status',)


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ('id', 'product', 'image', 'created_at', 'updated_at')
    search_fields = ('product',)
    list_editable = ('image',)