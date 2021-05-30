"""
Domain model for order allocation service. 

"""

from typing import Optional, List, Set
from datetime import date
from dataclasses import dataclass

from src.utils.logger import log
from src.allocation.domain import events

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

    def allocate(self, line: OrderLine):
        """
        Allocates part of a batch to the specified order line.

        """
        if self.can_allocate(line):
            self._allocations.add(line)
        else:
            raise OutOfStock(
                "Cannot allocate to this batch: skus do not "
                "match or requested qty is less than available qty."
            )

    def deallocate(self, line: OrderLine):
        if line in self._allocations:
            self._allocations.remove(line)
        else:
            raise OrderNotFound(
                f"Could not de-allocate order line; does not exist in this batch."
            )

    def deallocate_one(self) -> OrderLine:
        return self._allocations.pop()

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity

    def can_allocate(self, line: OrderLine) -> bool:
        return self.sku == line.sku and self.available_quantity >= line.qty


class Product:
    """
    Our chosen aggregate for this domain service.
    This will be the single entrypoint into our domain model.
    """

    def __init__(self, sku: str, batches: List[Batch], version_number: int = 0):
        self.sku = sku
        self.batches = batches
        self.version_number = version_number
        self.events = []  # type: List[events.Event]

    def allocate(self, line: OrderLine) -> str:
        """
        This implements our earlier domain service for 'allocate'.
        """
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
            batch.allocate(line)
            self.version_number += 1
            return batch.reference
        except StopIteration:
            self.events.append(events.OutOfStock(line.sku))
            return None

    def change_batch_quantity(self, ref: str, qty: int):
        batch = next(b for b in self.batches if b.reference == ref)
        batch._purchased_quantity = qty
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
            self.events.append(
                events.AllocationRequest(line.orderid, line.sku, line.qty)
            )