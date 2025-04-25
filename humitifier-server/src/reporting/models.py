from decimal import Decimal

from django.db import models


class CostsScheme(models.Model):

    name = models.CharField(max_length=100)

    cpu = models.DecimalField("Price per CPU", max_digits=10, decimal_places=2)
    memory = models.DecimalField(
        "Price per 1Gb memory", max_digits=10, decimal_places=2
    )
    storage = models.DecimalField(
        "Price per 1Tb storage", max_digits=10, decimal_places=2
    )

    redundant_storage = models.BooleanField(default=False)

    linux = models.DecimalField("Price for Linux", max_digits=10, decimal_places=2)
    windows = models.DecimalField("Price for Windows", max_digits=10, decimal_places=2)

    @property
    def storage_per_gb(self) -> Decimal:
        return self.storage / 1024

    def __str__(self):
        return self.name
