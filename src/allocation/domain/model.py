"""
Domain model for order allocation service. 

"""

from typing import Optional, List
from datetime import date
from dataclasses import dataclass

from src.utils.logger import log


# -----------------
# DOMAIN EXCEPTIONS
# -----------------
class OrderNotFound(Exception):
    pass


class OutOfStock(Exception):
    pass


# --------------
# DOMAIN OBJECTS
# --------------
@dataclass(
    unsafe_hash=True
)  # must set unsafe_hash or this gets marked as unhashable type
class OrderLine:
    """
    Represents a line on a customer product order.

    """

    orderid: str
    sku: str
    qty: int


class Batch:
    """
    Represents a batch of stock ordered by the purchasing department,
    en route from supplier to warehouse.

    """

    # NOTE: with __eq__ and __hash__, we make explicit that Batch
    # is an entity (instances have persistant identities even if
    # their values change); in this case the identity is specified
    # by self.reference
    def __eq__(self, other):
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __hash__(self):
        return hash(self.reference)

    # NOTE: with __gt__ we get to override how sorted() acts on this object,
    # i.e. how it determines whether one instance is 'greater' than another;
    # here we sort on eta, with earlier eta coming first (None = already in stock)
    def __gt__(self, other):
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def __init__(self, ref: str, sku: str, qty: int, eta: Optional[date]):
        """
        Parameters
        ----------
        reference : str
            Unique identifying reference number for this batch.

        sku : str
            Stock keeping unit, identifing the product in this batch.

        eta : str
            Estimated time of arrival if shipment; None if already in-stock.

        """

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
        else:
            raise

            log.info(
                "Cannot allocate to this batch: skus do not "
                "match or requested qty is less than available qty."
            )
            return False

    def deallocate(self, line: OrderLine):
        if line in self._allocations:
            self._allocations.remove(line)
        else:
            raise OrderNotFound(
                f"Could not de-allocate order line; does not exist in this batch."
            )

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and self.available_quantity >= line.qty


# ---------------
# DOMAIN SERVICES
# ---------------
def allocate(line: OrderLine, batches: List[Batch]) -> str:
    try:
        batch = next(b for b in sorted(batches) if b.can_allocate(line))
        batch.allocate(line)
        return batch.reference
    except:
        raise OutOfStock(f"Out of stock for sku {line.sku}")