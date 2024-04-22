from django.core.cache import cache
from django.db.models.signals import post_save, post_delete
from django.dispatch import Signal, receiver
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from products.models import Product

VIEWED = "viewed"

product_viewed = Signal()


@receiver(post_save, sender=Product, dispatch_uid='add_to_json')
def add_product_to_json_field(sender, instance, **kwargs):

    new_data = {
        f"{instance.id}": {
            "slug": instance.slug,
            "img_public_id": instance.main_image.public_id
        }
    }
    parent = instance.parent
    parent.all_products_json.update(new_data)
    parent.save()


@receiver(post_delete, sender=Product)
def remove_product_from_json_field(sender, instance, **kwargs):

    parent = instance.parent
    parent.all_products_json.pop(str(instance.id))
    parent.save()


def increment_product_views(product):
    """
    Increments Product.views.
    The counter is primarily saved in cache.
    The db is updated once per hour.
    """
    cache_view_count_key = f"{product.pk}_view_count"
    cache_last_saved_key = f"{product.pk}_view_count_last_saved"

    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    last_saved = cache.get(cache_last_saved_key) or '1900-01-01 00:00:00'
    view_count = cache.get(cache_view_count_key) or product.views
    view_count += 1
    cache.set(cache_view_count_key, view_count, 60000)
    if parse_datetime(current_time) - parse_datetime(last_saved) > timezone.timedelta(hours=1):
        product.views = view_count
        product.save()
        cache.set(cache_last_saved_key, current_time, 60000)


def add_to_viewed(sender, session, product, **kwargs):
    """
    Under key VIEWED in django session instance we keep track of primary keys
    of all ProductVariants viewed by a particular user within the last hour.
    This function checks whether the key for 'product' already exists
    in the VIEWED dict and if not, it appends it as a key with a value of
    the current time stamp.
    """
    if not session.get(VIEWED):
        session[VIEWED] = {}

    # Django serializes session data using JSON, so convert
    # the pk to str (since it will be stored as key)
    pk = str(product.pk)

    if session[VIEWED].get(pk):
        return

    session[VIEWED][pk] = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    session.modified = True

    # since it was a 'valid' view, increment the counter for product
    increment_product_views(product=product)


def delete_redundant_data(sender, session, **kwargs):
    """
    Deletes data for Products viewed more than 1 hour ago (see description of
    add_to_viewed function for reference).
    """
    if not session.get(VIEWED):
        return

    current_time = timezone.now().strftime('%Y-%m-%d %H:%M:%S')
    session[VIEWED] = {
        product_id: last_viewed for product_id, last_viewed in session[VIEWED].items()
        if parse_datetime(current_time) - parse_datetime(last_viewed) < timezone.timedelta(hours=1)
    }
    session.modified = True


product_viewed.connect(delete_redundant_data)
product_viewed.connect(add_to_viewed)
