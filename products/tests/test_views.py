from django.test import TransactionTestCase
from django.urls import reverse

from products.models import Product, Category, Campaign


class BaseTestCase(TransactionTestCase):
    fixtures = ["campaign.json", "category.json", "parent_product.json", "product.json",
                "color.json", "image.json", "size.json", "size_group.json", "stock.json"]


class ProductDetailTestCase(BaseTestCase):
    def test_queries_count(self):
        """
        Test that there are exactly 8 db queries:
        4 for the view:
        - 'products_product',
        - 'products_stock',
        - 'products_category',
        - 'products_images',

        + 4 own Django for session management.
        """
        with self.assertNumQueries(8):
            self.client.get(
                reverse(
                    "products:product_detail",
                    kwargs={'slug': 'strapless-dress-sky-blue'}
                )
            )

    def test_product_obj(self):
        product_from_db = Product.objects.get(slug='strapless-dress-deep-red')
        response = self.client.get(
            reverse(
                "products:product_detail",
                kwargs={'slug': 'strapless-dress-deep-red'}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('product'), product_from_db)

    def test_get_queryset_for_unavailable_product(self):

        product_from_db = Product.objects.get(slug='strapless-dress-sky-blue')
        response = self.client.get(
            reverse(
                "products:product_detail",
                kwargs={'slug': 'strapless-dress-sky-blue'}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context.get('product'), product_from_db)

    def test_categories(self):
        """
        Test that categories are correctly added to the context.
        """
        response = self.client.get(
            reverse(
                "products:product_detail",
                kwargs={'slug': 'strapless-dress-sky-blue'}
            )
        )
        self.assertIn('categories', response.context)
        self.assertEqual(len(response.context.get('categories')), 2)

    def test_non_existent_product(self):
        """
        Test that request for a non-existent product returns 404.
        """
        response = self.client.get(
            reverse(
                "products:product_detail",
                kwargs={'slug': 'non-existent-product-slug'}
            )
        )
        self.assertContains(
            response=response,
            text="Requested page has not been found.",
            count=1,
            status_code=404
        )


class ProductListTestCase(BaseTestCase):
    def test_queries_count(self):
        """
        Test that there are exactly 8 db queries:
        - 'products_product',
        - 'products_stock',
        - 'products_category',
        - 'products_images',
        - 'products_size',
        - 'products_sizegroup'
        and two subqueries
        """
        with self.assertNumQueries(8):
            self.client.get(
                reverse(
                    "products:product_list",
                )
            )

    def test_queries_count_with_query_string(self):
        """
        Same as above but with query params.
        Same number of queries expected.
        """
        with self.assertNumQueries(8):
            self.client.get(
                reverse(
                    "products:product_list",
                ) + "?color=1,2&size=4"
            )

    def test_get_queryset(self):
        """
        Only available products should be listed, so products with pk=7, 11
        shouldn't be in the queryset
        """
        products_from_db = Product.objects.exclude(pk__in=[7, 11])
        response = self.client.get(
            reverse(
                "products:product_list",
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context.get('products')), list(products_from_db))


class CampaignProductListTestCase(BaseTestCase):
    def test_queries_count(self):
        """
        Test that there are exactly 9 db queries:
        same as in ProductListTestCase plus
        one additional for 'products_campaign'.
        """
        with self.assertNumQueries(9):
            self.client.get(
                reverse(
                    "products:product_list_for_campaign",
                    kwargs={"slug": "new-collection"}
                )
            )

    def test_queries_count_non_existent_campaign(self):
        """
        Test that only one query is executed when Campaign with
        a given slug does not exist.
        """
        with self.assertNumQueries(1):
            self.client.get(
                reverse(
                    "products:product_list_for_campaign",
                    kwargs={"slug": "non-existent"}
                )
            )

    def test_get_queryset_campaign_view(self):
        # Campaign 'New Collection' so products with parent_pk=1, 2, 4, 5, 6 but only available so excluding pk=7,11
        products_from_db = Product.objects.exclude(pk__in=[7, 11]).filter(parent__in=[1, 2, 4, 5, 6])
        response = self.client.get(
            reverse(
                "products:product_list_for_campaign",
                kwargs={'slug': 'new-collection'}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context.get('products')), list(products_from_db))

        # Campaign 'Winter Sale' so products with parent_pk=3 but only available so excluding pk=7,11
        products_from_db = Product.objects.exclude(pk__in=[7, 11]).filter(parent=3)
        response = self.client.get(
            reverse(
                "products:product_list_for_campaign",
                kwargs={'slug': 'winter-sale'}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context.get('products')), list(products_from_db))


class CategoryProductListTestCase(BaseTestCase):
    def test_queries_count(self):
        """
        Test that there are exactly 10 db queries:
        same as in ProductListTestCase plus two additional
        for 'products_category' (for filtering products
        by category and for providing category queryset).
        """
        with self.assertNumQueries(10):
            self.client.get(
                reverse(
                    "products:product_by_category_list",
                    kwargs={"path": "dresses/summer-dresses"}
                )
            )
        with self.assertNumQueries(10):
            self.client.get(
                reverse(
                    "products:product_by_category_list",
                    kwargs={"path": "trousers"}
                )
            )

    def test_get_queryset(self):
        # Category 'dresses' so products with parent_pk=1, 2, 6 but only available so excluding pk=7,11
        products_from_db = Product.objects.exclude(pk__in=[7, 11]).filter(parent__in=[1, 2, 6])
        response = self.client.get(
            reverse(
                "products:product_by_category_list",
                kwargs={'path': 'dresses'}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context.get('products')), list(products_from_db))

        # Category 'floral-dresses' so products with parent_pk=1, but only available so excluding pk=7,11
        products_from_db = Product.objects.exclude(pk__in=[7, 11]).filter(parent=1)
        response = self.client.get(
            reverse(
                "products:product_by_category_list",
                kwargs={'path': 'dresses/floral-dresses'}
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context.get('products')), list(products_from_db))


class SearchProductListTestCase(BaseTestCase):
    def test_queries_count(self):
        """
        Test that there are exactly 7 db queries:
        same as in ProductListTestCase minus one for
        'products_category' (it's not used here)
        """
        with self.assertNumQueries(7):
            self.client.get(
                reverse(
                    "products:search_list",
                ) + '?q=chic+dress'
            )

    def test_get_queryset(self):
        """
        Only available products should be listed, so products with pk=7, 11
        shouldn't be in the queryset
        """
        products_from_db = Product.objects.exclude(pk__in=[7, 11]).filter(
            parent__search_keywords__icontains='wool'
        )
        response = self.client.get(
            reverse(
                "products:search_list"
            ) + "?q=wool"
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context.get('products')), list(products_from_db))


class MainPageTestCase(BaseTestCase):
    def test_queries_count(self):
        """
        Test that there are exactly 6 db queries:
        4 for the view:
        - 2 x 'products_product',
        - 2 x 'products_stock',
        - 'products_category',
        - 'products_campaign',
        """
        with self.assertNumQueries(6):
            self.client.get(
                reverse(
                    "products:main_page",
                )
            )

    def test_context_data(self):
        response = self.client.get(
            reverse(
                "products:main_page",
            )
        )

        self.assertEqual(response.status_code, 200)
        # only main categories
        self.assertEqual(
            list(Category.objects.filter(pk__in=[1, 4, 8, 10])),
            list(response.context.get('categories'))
        )
        # only active campaigns
        self.assertEqual(
            list(Campaign.objects.filter(pk__in=[1, 2])),
            list(response.context.get('campaigns'))
        )
        unavailable_product = Product.objects.get(pk=7)
        self.assertNotIn(
            unavailable_product,
            list(response.context.get('new_arrivals'))
        )
        self.assertNotIn(
            unavailable_product,
            list(response.context.get('most_popular'))
        )
        self.assertNotEqual(
            list(response.context.get('most_popular')),
            list(response.context.get('new_arrivals'))
        )





