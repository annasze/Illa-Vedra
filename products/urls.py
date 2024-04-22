from django.urls import re_path, path, include

from . import views

app_name = "products"

urlpatterns = [
    re_path(r'^p/(?P<slug>[-\w]+)/$', views.ProductDetail.as_view(), name='product_detail'),
    path('', views.main_page, name='main_page'),
    path(
        'products/',
        include(
            [
                path('', views.ProductList.as_view(), name='product_list'),
                path('search/', views.ProductSearchList.as_view(), name='search_list'),
                re_path(
                    r'^(?P<path>[\w/-]+)/$',
                    views.ProductByCategoryList.as_view(),
                    name='product_by_category_list'
                ),
            ]
        )
    ),
    path('campaign/<slug>/', views.ProductByCampaignList.as_view(), name='product_list_for_campaign'),
]
