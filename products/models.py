from __future__ import annotations

import re
from typing import Iterable

from cloudinary.models import CloudinaryField
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Case, When, F, DecimalField
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from mptt.fields import TreeForeignKey
from mptt.managers import TreeManager
from mptt.models import MPTTModel


class ParentProduct(models.Model):
    """
    A class to represent a non-sellable product.
    Most often a particular product (f.e a dress) comes in many colors,
    so in order to save database memory, ParentProduct class stores data common
    for all children Products.
    Fields:
    ----------
     category: ForeignKey
        groups products by type, f.e. 'dresses', 'sweaters',
     name: CharField
        self-explanatory,
     description, fabric_info, sizes_info: TextField
        optional descriptive data: an overall product description,
        information about fabric and information about size,
     campaign: ForeignKey
        it's like a batch of products, f.e. 'spring collection', 'sale',
     all_products_json: JSONField
        an automatically updated (via post_save signal) json field,
        which stores data for all children products, so that Products can
        easily fetch the data related to its siblings.
        e.g.:
        {
            "9": {
                "slug": "pencil-dress-bottle-green",
                "img_public_id": "lmuckfapvaz80u2xhftn"
            },
            "10": {
                "slug": "pencil-dress-deep-blue",
                "img_public_id": "tho4pqom8nux9r6ycb93"
            }
        }
     search_keywords: CharField
        a string of words used as keywords in a search bar, for a more
        efficient search, f.e.: 'jumper jersey pullover woolly sweater'.
    """
    category = models.ForeignKey(
        'Category',
        verbose_name=_('Category'),
        on_delete=models.SET_NULL,
        null=True,
        help_text=_("F.e.: 'dresses', 'skirts', etc.")

    )
    name = models.CharField(_('Name'), max_length=30, unique=True)
    description = models.TextField(
        _('Description'),
        blank=True,
        help_text=_("An optional description.")
    )
    fabric_info = models.TextField(
        _('Information about fabric'),
        blank=True,
        help_text=_("An optional description of fabric care, "
                    "composition of the fabric, etc.")
    )
    sizes_info = models.TextField(
        _('Information about sizes'),
        blank=True,
        help_text=_("An optional description of sizes,"
                    "f.e. chest width in size 38: 92 cm.")
    )
    campaign = models.ForeignKey(
        'Campaign',
        verbose_name=_('Campaign'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    all_products_json = models.JSONField(default=dict, blank=True, editable=False)
    search_keywords = models.CharField(
        max_length=192,
        verbose_name=_('Keywords for product search'),
        blank=True,
        help_text=_("f.e.: 'jumper jersey pullover woolly sweater' or "
                    "'woolen cashmere winter'"
                    "The product will appear on the search list if the user "
                    "types any of the words that you put here.")
    )

    def __str__(self):
        return str(self.name)

    class Meta:
        verbose_name_plural = _('Parent Products')


class ProductQueryset(models.QuerySet):
    """
    This queryset is used as a custom Manager for Product.
    """
    def available(self):
        return self.filter(
            stock__quantity__gt=0
        ).distinct()

    def for_categories(self, categories: Iterable[Category]):
        return self.filter(
            parent__category__in=categories
        )

    def for_campaign(self, campaign: Campaign):
        return self.filter(
            parent__campaign=campaign,
        )

    def for_search(self, keywords: list[str]):
        q = Q()
        for word in keywords:
            q |= Q(parent__search_keywords__icontains=word)

        return self.filter(q).distinct()

    def effective_price(self):
        """
        This annotation is used to provide an accurate
        comparison when ordering Products by price.
        """
        return self.annotate(
            effective_price=Case(
                When(
                    discounted_price__isnull=False,
                    then=F('discounted_price')
                ),
                default=F('price'),
                output_field=DecimalField()
            )
        )


class Product(models.Model):
    """
    Attributes
    ----------
    style : CharField
        it's what distinguishes Products of the same ParentProduct from one another.
        See examples in help_text of the field.
    color : ForeignKey
        Main color of the product, used just for filtering, it doesn't have to be unique.
    price, discounted_price, slug - self-explanatory
    main_image: CloudinaryField
        Main image of the product, it is saved here to avoid unnecessary additional db querying,
        since most of the time only one image per product will be used. Also, it ensures that
        no product is left without image.
    views: PositiveIntegerField
        Number of times the product was viewed by the users. It is used in sorting
         as a 'popularity' parameter.
    """
    parent = models.ForeignKey(
        ParentProduct,
        verbose_name=_("Parent Product"),
        on_delete=models.CASCADE
    )
    style = models.CharField(
        _("Style"),
        max_length=15,
        help_text=_("f.e.: 'polka dot', 'royal blue' or just simply 'black'.")
    )
    color = models.ForeignKey(
        "Color",
        verbose_name=_("Color"),
        on_delete=models.SET_NULL,
        help_text=_("Color used for filtering"),
        null=True
    )
    price = models.DecimalField(_("Price"), max_digits=8, decimal_places=2)
    discounted_price = models.DecimalField(
        _("Discounted price"),
        max_digits=8,
        decimal_places=2,
        blank=True,
        null=True
    )
    slug = models.SlugField(max_length=192, unique=True, blank=True, editable=False)
    main_image = CloudinaryField(_("Main image"))
    views = models.PositiveIntegerField(_("Number of views"), default=0, editable=False)
    sizes = models.ManyToManyField("Size", verbose_name=_("Sizes"), through="Stock")

    objects = models.Manager()
    custom_manager = ProductQueryset.as_manager()

    @property
    def name(self):
        return str(self)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                name="unique_parent_style",
                fields=["parent", "style"],
            ),
        ]
        ordering = ('-views',)

    def get_absolute_url(self):
        return reverse('products:product_detail', args=[self.slug])

    def save(self, *args, **kwargs):
        """ Generates slug at object creation."""
        if not self.pk:
            self.slug = slugify("%s %s" % (self.parent.name, self.style))

        super().save(*args, **kwargs)

    def clean(self):
        if self.discounted_price and self.discounted_price >= self.price:
            raise ValidationError(
                _("Discounted price: (%(discounted_price)s) "
                  "must be lower than price: (%(price)s)."),
                code="invalid_discounted_price",
                params={
                    "price": self.price,
                    "discounted_price": self.discounted_price
                },
            )

    def __str__(self):
        return "%s - %s" % (self.parent, self.style)


class CategoryManager(TreeManager):
    def root_and_path_categories(self, crumb):
        """
        Returns all root categories (categories with no parent)
        plus all descendants of the selected root category.
        """
        selected_category = self.get(path_crumb=crumb)
        categories = self.filter(parent__isnull=True) | self.filter(tree_id=selected_category.tree_id)

        return categories


class Category(MPTTModel):
    """
    This model uses an external django app - django-mptt, which
    facilitates storing and retrieving models defined as a tree
    structure.

    Fields:
    ----------
    path_crumb: CharField
        A slugified name of the category, the last part of the path.
        The path for a category contains 'path_crumbs' of all its ancestors, f.e.
        the path for a category named "Floral dresses" could be:
        dresses/summer-dresses/floral-dresses/
    """
    name = models.CharField(_("Name"), max_length=32, unique=True)
    parent = TreeForeignKey(
        "self",
        verbose_name=_("Parent category"),
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="children",
    )
    path_crumb = models.CharField(max_length=64, blank=True, unique=True, editable=False)

    objects = CategoryManager()

    class Meta:
        verbose_name_plural = _('Categories')

    def save(self, *args, **kwargs):
        if not self.pk:
            self.path_crumb = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        path = "/".join(ancestor.path_crumb for ancestor in self.get_ancestors(include_self=True))

        return reverse('products:product_by_category_list', args=[path])

    def __str__(self):
        return str(self.name)


class Color(models.Model):
    """
    Colors for filtering.
    Defining colors as a separate model instead of just list of choices
    allows adding more colors in the future.
    """
    name = models.CharField(_("Name"), max_length=15, unique=True)
    hex_code = models.CharField(
        _("Hex color code"),
        max_length=7,
        unique=True,
        help_text=_("A hex code for the desired color shade. "
                    "It starts with # and contains 6 characters. "
                    "Visit https://www.w3schools.com/colors/colors_picker.asp"
                    "to find out more."),
    )

    def __str__(self):
        return str(self.name)

    def clean(self):
        pattern = r'^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$'
        if re.search(pattern, self.hex_code) is None:
            raise ValidationError(
                _("The provided hex_code: (%(hex_code)s) is invalid. "
                  "Check the code and try again."),
                code="invalid_hex_code",
                params={"hex_code": self.hex_code},
            )


class Image(models.Model):
    product = models.ForeignKey(
        Product,
        verbose_name=_("Product"),
        on_delete=models.CASCADE,
        related_name="images"
    )
    url = CloudinaryField(_("Image url"))

    def __str__(self):
        return str(self.product)


class Campaign(models.Model):
    name = models.CharField(_("Name"), max_length=32, unique=True)
    slug = models.SlugField(max_length=32, unique=True, blank=True, editable=False)
    image = CloudinaryField(_("Image"))
    description = models.TextField(
        _('Description'),
        blank=True,
        help_text=_("An optional description.")
    )
    is_active = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """ Generates slug at object creation."""
        if not self.pk:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class SizeGroup(models.Model):
    """
    Groups provide a better organization of sizes on the filter list,
    we can then place them in separate containers.
    """
    name = models.CharField(
        _("Name"),
        max_length=15,
        unique=True,
        help_text=_("f.e. 'numerical', 'literal'.")
    )

    def __str__(self):
        return str(self.name)

    class Meta:
        ordering = ("pk",)


class Size(models.Model):
    """
    Sizes for filtering.
    """
    name = models.CharField(_("Name"), max_length=15, unique=True)
    group = models.ForeignKey(
        SizeGroup,
        on_delete=models.CASCADE,
        related_name="sizes",
        verbose_name=_("Related Size Group"),
    )

    class Meta:
        ordering = ('group', "pk")

    def __str__(self):
        return str(self.name)


class Stock(models.Model):
    """
    An intermediate model with an additional attribute
    quantity.
    """
    product = models.ForeignKey(
        Product,
        verbose_name=_("Product"),
        on_delete=models.CASCADE,
        related_name="stock",
    )
    size = models.ForeignKey(
        Size,
        verbose_name=_("Size"),
        on_delete=models.CASCADE,
        related_name="stock",
    )
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return "%s, quantity: %s" % (self.product, self.quantity)


