from django import forms
from django.contrib import admin, messages
from django.shortcuts import render
from django.utils.translation import gettext_lazy as _, ngettext
from mptt.admin import DraggableMPTTAdmin

from . import models


class ProductInline(admin.TabularInline):
    model = models.Product
    extra = 6
    verbose_name = _("Product")
    verbose_name_plural = _("Products")


class StockInline(admin.TabularInline):
    model = models.Stock
    extra = 8
    verbose_name = _("Stock")
    verbose_name_plural = _("Stock")


class SizesInline(admin.TabularInline):
    model = models.Size
    extra = 8

    verbose_name = _("Size")
    verbose_name_plural = _("Sizes")


class SubCategoryInline(admin.TabularInline):
    model = models.Category
    extra = 4
    verbose_name = _("Subcategory")
    verbose_name_plural = _("Subcategories")


@admin.register(models.ParentProduct)
class ParentProductModelAdmin(admin.ModelAdmin):
    model = models.ParentProduct
    inlines = [ProductInline]
    list_display = ['name', 'category', 'campaign']
    search_fields = ['name', 'description']
    actions = ['change_campaign']

    class ChangeCampaignForm(forms.Form):
        campaign = forms.ModelChoiceField(
            queryset=models.Campaign.objects.all(),
            label='Select Campaign'
        )

    def change_campaign(self, request, queryset):
        if 'apply' in request.POST:
            form = self.ChangeCampaignForm(request.POST)
            if form.is_valid():
                new_campaign = form.cleaned_data['campaign']
                queryset.update(campaign=new_campaign)
                self.message_user(
                    request,
                    ngettext(
                        "Campaign updated successfully for %d Parent Product.",
                        "Campaign updated successfully for %d Parent Products.",
                        queryset.count(),
                    )
                    % queryset.count(),
                    messages.SUCCESS,
                )
                return
        else:
            form = self.ChangeCampaignForm()

        return render(
            request,
            'admin/change_campaign.html',
            {
                'form': form,
                'parent_products': queryset
            }
        )

    change_campaign.short_description = "Change campaign"


@admin.register(models.Product)
class ProductModelAdmin(admin.ModelAdmin):
    model = models.Product
    inlines = [StockInline]
    list_display = [
        'parent', 'style', 'color', 'price', 'discounted_price', 'views',
    ]
    ordering = ['parent']
    search_fields = ['parent__name', 'parent__id', "style"]


@admin.register(models.Category)
class CategoryModelAdmin(DraggableMPTTAdmin):
    mptt_level_indent = 20
    inlines = [SubCategoryInline]


@admin.register(models.SizeGroup)
class SizeGroupModelAdmin(admin.ModelAdmin):
    inlines = [SizesInline]


@admin.register(models.Size)
class SizeModelAdmin(admin.ModelAdmin):
    model = models.Size
    list_display = ['name', 'group']
    search_fields = ['name', 'group']


@admin.register(models.Color)
class ColorModelAdmin(admin.ModelAdmin):
    model = models.Color
    list_display = ['name', 'hex_code']
    search_fields = ['name', 'hex_code']


@admin.register(models.Stock)
class StockModelAdmin(admin.ModelAdmin):
    model = models.Stock
    list_display = ['id', 'product', 'size', "quantity"]
    search_fields = ['id', 'product', 'size', "quantity"]


@admin.register(models.Image)
class ImageModelAdmin(admin.ModelAdmin):
    model = models.Image
    list_display = ['id', 'product', 'url']
    search_fields = ['product']


@admin.register(models.Campaign)
class CampaignModelAdmin(admin.ModelAdmin):
    model = models.Campaign
    list_display = ['name', 'is_active']
