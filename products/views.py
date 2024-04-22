from django.db.models import Max, Prefetch
from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView, ListView

from products import signals
from products.filter import ProductFilter
from products.models import Product, Category, Color, SizeGroup, Campaign, Stock


def main_page(request):

    # fetch only main Categories (without parent)
    categories = Category.objects.filter(parent__isnull=True)
    # fetch only active Campaigns
    campaigns = Campaign.objects.filter(is_active=True)

    base_queryset = Product.custom_manager.available().select_related(
        'parent').prefetch_related(
        Prefetch("stock", queryset=Stock.objects.select_related("size")),
    )
    new_arrivals = base_queryset.order_by('-pk')[:10]
    # ordering by the most popular Products is the default set in Meta, so no 'order_by' needed
    most_popular = base_queryset[:10]

    return render(
        request,
        'main_page.html',
        {
            'categories': categories,
            'campaigns': campaigns,
            'new_arrivals': new_arrivals,
            'most_popular': most_popular,
        }
    )


class ProductList(ListView):
    filter = ProductFilter
    context_object_name = "products"
    paginate_by = 24
    ordering_param_name = "sorting"
    ordering_options = {
        "popularity": "-views",
        "price_ascending": "effective_price",
        "price_descending": "-effective_price",
        "newest": "-pk",
    }
    template_name = 'products/product_list/product_list.html'

    def get_queryset(self):
        """
        Fetch only available Products.
        Prefetch relevant data to save db queries.
        """
        self.queryset = Product.custom_manager.available().select_related(
            'parent').prefetch_related(
            Prefetch("stock", queryset=Stock.objects.select_related("size")),
        )

        # apply filters if applicable
        if q := self.get_Q_object():
            self.queryset = self.queryset.filter(q).distinct()

        # apply ordering
        ordering = self.get_ordering()
        # if ordering by price, apply effective_price annotation
        # for a correct comparison between discounted and regular price
        if ordering.find('price') != -1:
            self.queryset = self.queryset.effective_price()

        return self.queryset.order_by(ordering)

    def get_Q_object(self):
        """
        Returns a django Q object for filtering
        based on query parameters
        """
        return ProductFilter(**self.request.GET).get_Q()

    def get_context_data(self, *, object_list=None, **kwargs):
        """
        Add data for filtering.
        """
        context = super().get_context_data(object_list=None, **kwargs)

        context['categories'] = Category.objects.filter(parent__isnull=True)
        context['colors'] = Color.objects.all()
        context['size_groups'] = SizeGroup.objects.prefetch_related('sizes')
        context["max_price"] = self.queryset.aggregate(Max("price"))['price__max'] or 999
        context['ordering_options'] = {k: k.replace("_", " ") for k in self.ordering_options}
        context['ordering_param_name'] = self.ordering_param_name

        return context

    def get_ordering(self):
        """
        Get ordering from query param if present,
        use default otherwise.
        """
        ordering = self.request.GET.get(self.ordering_param_name) or ""

        return self.ordering_options.get(ordering, "-views")


class ProductByCampaignList(ProductList):
    template_name = 'products/product_list/product_list_campaign.html'

    def get_queryset(self):
        """
        Fetch Campaign object first instead of filtering directly:
        - only one query is executed when Campaign object for a given slug
          does not exist,
        - if filtering Product queryset directly results in an empty queryset,
          it's impossible to distinguish if the Campaign object does not exist
          or there are no results for a given query params.
        """
        self.queryset = super().get_queryset()
        slug = self.kwargs.get("slug")
        campaign = get_object_or_404(Campaign, slug=slug, is_active=True)

        return self.queryset.for_campaign(campaign)

    def get_context_data(self, *, object_list=None, **kwargs):
        """ Add Campaign object """
        context = super().get_context_data(object_list=None, **kwargs)
        context['campaign'] = Campaign.objects.get(slug=self.kwargs.get("slug"))

        return context


class ProductByCategoryList(ProductList):
    def get_queryset(self):
        """
        Same approach as in ProductByCampaignList.
        """
        self.queryset = super().get_queryset()
        # example path: dresses/summer-dresses/floral-dresses,
        # then crumb = "floral-dresses"
        crumb = self.kwargs.get("path", "").split("/")[-1]
        category = get_object_or_404(Category, path_crumb=crumb)
        categories = category.get_descendants(include_self=True)

        return self.queryset.for_categories(categories)

    def get_context_data(self, *, object_list=None, **kwargs):
        """ Add Categories queryset """

        context = super().get_context_data(object_list=None, **kwargs)
        crumb = self.kwargs.get("path", "").split("/")[0]
        context['categories'] = Category.objects.root_and_path_categories(crumb)

        return context


class ProductSearchList(ProductList):
    template_name = 'products/product_list/search_list.html'

    def get_queryset(self):
        self.queryset = super().get_queryset()
        user_input = self.request.GET.get('q', '')
        keywords = user_input.strip(" ").split(" ")

        return self.queryset.for_search(keywords)


class ProductDetail(DetailView):
    context_object_name = "product"
    template_name = 'products/product_detail/product_detail.html'

    def get_queryset(self):
        """
        Fetch all products (not only available like in ListViews)
        so that the user can see f.e. a product added to
        bookmarks a week ago and currently out of stock,
        instead of 404.
        Prefetch relevant data to save db queries.
        """

        return Product.objects.select_related(
            'parent', 'parent__category').prefetch_related(
            Prefetch("stock", queryset=Stock.objects.select_related("size")),
            'images'
        )

    def get_context_data(self, **kwargs):
        """ Add categories bread crumb """
        context = super().get_context_data(**kwargs)
        # get object from context to avoid unnecessary db queries
        obj = context.get('object')
        categories = obj.parent.category.get_ancestors(include_self=True)
        context["categories"] = categories

        return context

    def render_to_response(self, context, **response_kwargs):
        """ Send signal to increment views counter """
        signals.product_viewed.send(
            sender=self.model,
            session=self.request.session,
            product=context.get(self.context_object_name),
        )
        return super().render_to_response(context, **response_kwargs)
