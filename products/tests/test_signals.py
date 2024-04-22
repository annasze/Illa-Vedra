import datetime

from django.core.cache import cache
from django.db.models import signals
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from freezegun import freeze_time

from products.models import Product, ParentProduct, Color, Category

VIEWED = "viewed"


class SignalTestCase(TestCase):
    def setUp(self):
        signals.post_save.disconnect(sender=Product, dispatch_uid='add_to_json')

        self.category = Category.objects.create(name="Dresses")
        self.color = Color.objects.create(name='blue')
        self.parent_product = ParentProduct.objects.create(
            category=self.category,
            name="Floral dress"
        )
        self.product_1 = Product.objects.create(
            parent=self.parent_product,
            style="royal blue",
            color=self.color,
            price=99,
        )
        self.product_1_url = reverse('products:product_detail', args=[self.product_1.slug])

        self.product_2 = Product.objects.create(
            parent=self.parent_product,
            style="sky blue",
            color=self.color,
            price=99,
        )
        self.product_2_url = reverse('products:product_detail', args=[self.product_2.slug])

        cache.clear()

    def test_add_to_viewed_VIEWED_is_empty(self):
        """
        Test that when the user views a Product for the first time,
         the timestamp is saved in session.
        """
        key = str(self.product_1.pk)

        self.assertEqual(self.client.session.get(VIEWED), None)
        self.client.get(self.product_1_url)
        self.assertIn(key, self.client.session.get(VIEWED))

        current_time = parse_datetime(
            timezone.now().strftime('%Y-%m-%d %H:%M:%S')
        )
        viewed_at = parse_datetime(
            self.client.session.get(VIEWED).get(key)
        )
        self.assertLess(current_time - viewed_at, timezone.timedelta(minutes=1))

    @freeze_time("2023-12-31 12:00:00")
    def test_add_to_viewed_product_revisited_shortly(self):
        """
        Test that when the user views the same Product again  in less than
        an hour, the timestamp in session does not change.
        """
        key = str(self.product_1.pk)

        # visit the url
        self.client.get(self.product_1_url)
        viewed_at = self.client.session.get(VIEWED).get(key)

        # revisit in 5 minutes
        with freeze_time("2023-12-31 12:05:00"):
            self.client.get(self.product_1_url)

        # timestamp should stay the same
        self.assertEqual(
            self.client.session.get(VIEWED).get(key),
            viewed_at
        )

    @freeze_time("2023-12-31 12:00:00")
    def test_add_to_viewed_product_revisited_in_more_than_1_hr(self):
        """
        Test that when the user views the same Product again
        in more than an hour, the timestamp in session will change
        """
        key = str(self.product_1.pk)

        # visit the url
        self.client.get(self.product_1_url)
        viewed_at = self.client.session.get(VIEWED).get(key)

        # revisit in 1 hour 1 minute
        with freeze_time("2023-12-31 13:01:00"):
            self.client.get(self.product_1_url)

        # timestamp should be updated
        self.assertNotEqual(
            viewed_at,
            self.client.session.get(VIEWED).get(key)
        )
        self.assertAlmostEqual(
            self.client.session.get(VIEWED).get(key),
            datetime.datetime(2023, 12, 31, 13, 1).strftime('%Y-%m-%d %H:%M:%S')
        )

    @freeze_time("2023-12-31 12:00:00")
    def test_delete_redundant_data(self):
        """
        Make sure that data for Product viewed more than 1 hour ago
        is no longer available in session.
        """
        key = str(self.product_1.pk)

        # visit the url
        self.client.get(self.product_1_url)

        viewed_at = self.client.session.get(VIEWED).get(key)

        # check in 59 minutes - record should still be in session
        with freeze_time("2023-12-31 12:59:00"):
            self.client.get(self.product_2_url)
        self.assertEqual(
            self.client.session.get(VIEWED).get(key),
            viewed_at
        )

        # check in 1h 5 s - record should be gone
        with freeze_time("2023-12-31 13:00:05"):
            self.client.get(self.product_2_url)
        self.assertEqual(
            self.client.session.get(VIEWED).get(key),
            None
        )

    def test_increment_product_views_cache(self):
        """
        Test that visiting the url updates its counter in cache
        """
        self.cache_key = f"{self.product_1.pk}_view_count"
        # visit the url
        self.client.get(self.product_1_url)
        self.assertEqual(cache.get(self.cache_key), 1)

    @freeze_time("2023-12-31 12:00:00")
    def test_increment_product_views_db(self):
        """
        Test that the counter number in db gets updated
        every one hour
        """

        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.views, 0)

        self.cache_key = f"{self.product_1.pk}_view_count"
        self.cache_last_saved_key = f"{self.product_1.pk}_view_count_last_saved"

        # set the counter in cache manually to 299 views
        cache.set(self.cache_key, 299, 6000)
        cache.set(self.cache_last_saved_key, "2023-12-31 12:00:00", 6000)

        with freeze_time("2023-12-31 13:00:05"):
            self.client.get(self.product_1_url)
        self.product_1.refresh_from_db()
        self.assertEqual(self.product_1.views, 300)
