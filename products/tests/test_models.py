from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.db.models import signals, Q
from django.shortcuts import get_object_or_404
from django.test import TestCase, TransactionTestCase

from products import models
from products.models import Product, Campaign, Category, Size, SizeGroup, ParentProduct


class ProductQuerysetTestCase(TestCase):
    fixtures = ["campaign.json", "category.json", "parent_product.json", "product.json",
                "color.json", "image.json", "size.json", "size_group.json", "stock.json"]

    def test_available(self):
        # products with pk=7 & 11 are unavailable,
        # so they shouldn't be in the Queryset
        queryset = Product.custom_manager.available()

        self.assertNotIn(Product.objects.filter(pk__in=[7, 11]), queryset)
        self.assertEqual(queryset.count(), Product.objects.count() - 2)
        self.assertEqual(list(queryset), list(Product.objects.exclude(pk__in=[7, 11])))

    def test_for_category(self):
        category = get_object_or_404(Category, path_crumb='summer-dresses')
        categories = category.get_descendants(include_self=True)
        queryset = Product.custom_manager.for_categories(categories)

        self.assertEqual(list(Product.objects.filter(parent__pk__in=[2, 6])), list(queryset))

    def test_for_campaign(self):
        # Products with pk: 1, 2, 4, 5, 6 should be in New collection
        campaign = get_object_or_404(Campaign, slug='new-collection')
        queryset = Product.custom_manager.for_campaign(campaign)
        self.assertEqual(list(Product.objects.filter(parent__pk__in=[1, 2, 4, 5, 6])), list(queryset))

    def test_for_search(self):
        queryset = Product.custom_manager.for_search(['chic'])
        self.assertEqual(list(Product.objects.filter(parent__pk__in=[1, 2, 5])), list(queryset))

        queryset = Product.custom_manager.for_search(['wool'])
        self.assertEqual(list(Product.objects.filter(parent__pk__in=[3, 5])), list(queryset))

        queryset = Product.custom_manager.for_search(['sleeveless', 'dress'])
        self.assertEqual(list(Product.objects.filter(parent__pk__in=[1, 2])), list(queryset))

        # check that all products are returned when the query string is empty
        queryset = Product.custom_manager.for_search([''])
        self.assertEqual(list(Product.objects.all()), list(queryset))

    def test_effective_price(self):
        queryset = Product.custom_manager.effective_price()

        # product with pk=12 has price=29.00 and discounted_price = 19.00
        # effective price should be 19.00
        product = queryset.get(pk=12)
        self.assertEqual(product.effective_price, 19.00)

        # product with pk=7 has price=99.00 and discounted_price = None
        # effective price should be 99.00
        product = queryset.get(pk=7)
        self.assertEqual(product.effective_price, 99.00)


class TransactionsTestCase(TransactionTestCase):
    fixtures = ["campaign.json", "category.json", "parent_product.json", "product.json",
                "color.json", "image.json", "size.json", "size_group.json", "stock.json"]

    def test_product_list_main_queryset(self):
        """
        Queryset in ProductList(ListView)
         Two queries expected:
        - 'products_product',
        - 'products_stock'.
        """
        with self.assertNumQueries(2):
            list(Product.custom_manager.available().select_related(
                'parent').prefetch_related('stock'))

    def test_product_list_category_queryset(self):
        """
         Three queries expected:
        - 'products_product',
        - 'products_stock',
        - 'products_category',
        """
        with self.assertNumQueries(3):
            queryset = Product.custom_manager.available().select_related(
                'parent').prefetch_related('stock')
            category = get_object_or_404(Category, path_crumb='dresses')
            categories = category.get_descendants(include_self=True)
            queryset = queryset.for_categories(categories)
            list(queryset)

    def test_product_list_campaign_queryset(self):
        """
         Three queries expected:
        - 'products_product',
        - 'products_stock',
        - 'products_campaign',
        """
        with self.assertNumQueries(3):
            queryset = Product.custom_manager.available().select_related(
                'parent').prefetch_related('stock')
            campaign = get_object_or_404(Campaign, slug='new-collection', is_active=True)

            queryset = queryset.for_campaign(campaign)
            list(queryset)

    def test_product_list_for_search_queryset(self):
        """
         Two queries expected:
        - 'products_product',
        - 'products_stock',
        """
        with self.assertNumQueries(2):
            queryset = Product.custom_manager.available().select_related(
                'parent').prefetch_related('stock')
            queryset = queryset.for_search(['sleeveless', 'dress'])
            list(queryset)

    def test_product_list_with_query_params(self):
        """
         Two queries expected:
        - 'products_product',
        - 'products_stock',
        """
        with self.assertNumQueries(2):
            queryset = Product.custom_manager.available().select_related(
                'parent').prefetch_related('stock')
            q = Q(color__in=[1, 2]) & (
                (Q(price__lte=199) & Q(discounted_price__isnull=True)) |
                Q(discounted_price__lte=199)
            )
            queryset = queryset.filter(q).distinct()
            list(queryset)

    def test_product_detail_get_object(self):
        """
         Three queries expected:
        - 'products_product',
        - 'products_stock',
        - 'products_images',
        """
        with self.assertNumQueries(3):
            queryset = Product.objects.select_related(
                'parent').prefetch_related('stock', 'images')
            queryset.get(slug='skin-tight-t-shirt-grey')


class CategoryTestCase(TestCase, Category):
    def setUp(self) -> None:
        self.category_dresses = models.Category.objects.create(
            name='Dresses',
        )
        self.category_summer_dresses = models.Category.objects.create(
            name='Summer dresses',
            parent=self.category_dresses,
        )
        self.category_trousers = models.Category.objects.create(
            name='Trousers',
        )
        self.category_business_trousers = models.Category.objects.create(
            name='Business trousers',
            parent=self.category_trousers
        )

    def test_path_crumb_created(self):
        """
        Test that path_crumb is correctly created
        """
        self.assertEqual(self.category_dresses.path_crumb, 'dresses')
        self.assertEqual(self.category_summer_dresses.path_crumb, 'summer-dresses')

    def test_path_crumb_after_update(self):
        """
        Test that path_crumb stays the same even if the category name is changed
        """
        self.assertEqual(self.category_dresses.path_crumb, 'dresses')
        self.category_dresses.name = 'Floral dresses'
        self.category_dresses.save()
        self.category_dresses.refresh_from_db()
        self.assertEqual(self.category_dresses.path_crumb, 'dresses')

    def test_get_absolute_url(self):
        self.assertIn('dresses/', self.category_dresses.get_absolute_url())
        self.assertIn('dresses/summer-dresses/', self.category_summer_dresses.get_absolute_url())

    def test_str(self):
        self.assertEqual(str(self.category_dresses), 'Dresses')
        self.assertEqual(str(self.category_summer_dresses), 'Summer dresses')

    def test_root_and_path_categories_manager_method(self):
        categories = Category.objects.root_and_path_categories(crumb="dresses")
        self.assertIn(self.category_dresses, categories)
        self.assertIn(self.category_summer_dresses, categories)
        self.assertIn(self.category_trousers, categories)    # it's a root category
        self.assertNotIn(self.category_business_trousers, categories)


class ColorTestCase(TestCase):
    def setUp(self) -> None:
        self.color_red = models.Color.objects.create(
            name="red",
            hex_code="#ff0000"
        )
        self.color_green = models.Color.objects.create(
            name="green",
            hex_code="#00ff00"
        )
        self.color_blue = models.Color.objects.create(
            name="blue",
            hex_code="#0000ff"
        )

    def test_str(self):
        self.assertEqual(str(self.color_blue), "blue")

    def test_correct_hex_code_is_set(self):
        orange = models.Color.objects.create(
            name="orange",
            hex_code="#ffa500"
        )
        orange.full_clean()
        orange.refresh_from_db()
        self.assertEqual(orange.hex_code, "#ffa500")

    def test_incorrect_hex_code_raises_error(self):
        orange = models.Color.objects.create(
            name="orange",
            hex_code="#fa500"
        )
        with self.assertRaises(ValidationError) as cm:
            orange.full_clean()
        self.assertIn(
            "'The provided hex_code: (%s) is invalid. "
            "Check the code and try again.'" % orange.hex_code,
            str(cm.exception)
        )


class SizeTestCase(TestCase):
    def setUp(self) -> None:
        self.size_group_numerical = SizeGroup.objects.create(
            name="Numerical"
        )
        self.size_group_literal = SizeGroup.objects.create(
            name="Literal"
        )
        self.size_40 = Size.objects.create(name="40", group=self.size_group_numerical)
        self.size_S = Size.objects.create(name="S", group=self.size_group_literal)
        self.size_38 = Size.objects.create(name="38", group=self.size_group_numerical)
        self.size_M = Size.objects.create(name="M", group=self.size_group_literal)
        self.size_36 = Size.objects.create(name="36", group=self.size_group_numerical)

    def test_str(self):
        self.assertEqual(str(self.size_group_numerical), "Numerical")
        self.assertEqual(str(self.size_36), "36")

    def test_sizes_ordering(self):
        """
        Test that sizes are correctly ordered: first by size_group pk in asc order,
        then by pk in asc order.
        """
        sizes = Size.objects.all()

        self.assertEqual(str(sizes[0]), "40")
        self.assertEqual(str(sizes[1]), "38")
        self.assertEqual(str(sizes[2]), "36")
        self.assertEqual(str(sizes[3]), "S")
        self.assertEqual(str(sizes[4]), "M")


class ProductTestCase(TestCase):
    def setUp(self) -> None:
        signals.post_save.disconnect(sender=Product, dispatch_uid='add_to_json')

        self.category = Category.objects.create(
            name='Dresses',
        )
        self.parent = ParentProduct.objects.create(
            category=self.category,
            name="Floral dress"
        )

        self.product = Product(
            parent=self.parent,
            style="sunflower",
            price=99,
        )
        self.product.save()

    def test_slug_created(self):
        self.assertEqual(self.product.slug, 'floral-dress-sunflower')

    def test_slug_after_name_update(self):
        """
        Test that slug stays the same even if the parent name is changed
        """
        self.parent.name = "Summer dress"
        self.parent.save()
        self.parent.refresh_from_db()
        self.assertEqual(self.product.slug, 'floral-dress-sunflower')

    def test_str(self):
        self.assertEqual(str(self.product), "Floral dress - sunflower")

    def test_name(self):
        self.assertEqual(self.product.name, "Floral dress - sunflower")

    def test_incorrect_discounted_price_raises_error(self):
        new_product = Product.objects.create(
            parent=self.parent,
            style="red",
            price=79,
            discounted_price=99,
        )
        with self.assertRaises(ValidationError) as cm:
            new_product.full_clean()
        self.assertIn(
            "Discounted price: (99) must be lower than price: (79).",
            cm.exception.messages
        )

    def test_parent_style_unique_constraint(self):
        with self.assertRaises(IntegrityError) as cm:
            models.Product.objects.create(
                parent=self.parent,
                style="sunflower",
                price=59,
            )
        self.assertIn("UNIQUE constraint failed", str(cm.exception))

    def test_get_absolute_url(self):
        self.assertIn("p/floral-dress-sunflower/", self.product.get_absolute_url())