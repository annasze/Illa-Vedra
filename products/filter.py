from django.db.models import Q


class ProductFilter:
    def __init__(self, **kwargs):
        self._q = Q()

        for k, v in kwargs.items():
            # in frontend, param values are represented as a string separated by commas, f.e.:
            # /?color=3,5,7, so take the first value from the list and split by a comma
            v = v[0].split(",")
            v = self.validate(v)
            if hasattr(self, "set_%s_filter" % k) and v:
                getattr(self, "set_%s_filter" % k)(v)

    @staticmethod
    def validate(param_values: list[str]):
        try:
            return list(map(int, param_values))
        except ValueError:
            return

    def set_price_gte_filter(self, price: list[int]):
        self._q &= (
                (Q(price__gte=price[0]) & Q(discounted_price__isnull=True)) |
                Q(discounted_price__gte=price[0])
        )

    def set_price_lte_filter(self, price: list[int]):
        self._q &= (
                (Q(price__lte=price[0]) & Q(discounted_price__isnull=True)) |
                Q(discounted_price__lte=price[0])
        )

    def set_color_filter(self, color: list[int]):
        if len(color) > 1:
            self._q &= Q(color__in=color)
        else:
            self._q &= Q(color=color[0])

    def set_size_filter(self, size: list[int]):
        if len(size) > 1:
            q = Q(stock__size__in=size)
        else:
            q = Q(stock__size=size[0])
        self._q &= q & Q(stock__quantity__gt=0)

    def get_Q(self):
        return self._q
