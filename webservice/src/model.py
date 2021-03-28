"""
Domain model for order allocation service. 

"""

from typing import Optional
from datetime import date
from dataclasses import dataclass

from webservice.utils.logger import log


@dataclass(frozen=True)
class OrderLine:
    """
    Represents a line on a customer product order.

    """

    orderid: str
    sku: str
    qty: int


class Batch:
    """
    Represents a batch of stock placed by the purchasing department,
    en route from supplier to warehouse.

    """

    def __init__(self, ref: str, sku: str, qty: int, eta: Optional[date]):
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = qty
        self._allocations = set()  # type: Set[OrderLine]

    def allocate(self, line: OrderLine) -> bool:
        """
        Allocates part of a batch to the specified order line.

        """
        if self.can_allocate(line):
            self._allocations.add(line)
            return True
        else:
            log.info(
                "Cannot allocate to this batch: skus do not "
                "match or requested qty is less than available qty."
            )
            return False

    def deallocate(self, line: OrderLine) -> bool:
        if line in self._allocations:
            self._allocations.remove(line)
            return True
        else:
            log.info("Could not de-allocate line; does not exist in this batch.")
            return False

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and self.available_quantity >= line.qty
