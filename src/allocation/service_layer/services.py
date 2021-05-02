from typing import Optional
from datetime import date

from src.utils.logger import log
from src.allocation.domain import model
from src.allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {batch.sku for batch in batches}


def add_batch(
    ref: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        uow.batches.add(model.Batch(ref, sku, qty, eta))
        uow.commit()


def allocate(
    orderid: str, sku: str, qty: int, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = model.OrderLine(orderid, sku, qty)
    with uow:
        batches = uow.batches.list()
        if not is_valid_sku(line.sku, batches):
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = model.allocate(line, batches)
        uow.commit()
    return batchref


def deallocate(orderid: str, sku: str, qty: int, uow: unit_of_work.AbstractUnitOfWork):
    # to scale, this would best be done by querying the allocations
    # table directly, but since we lack it in the repo, we'll use
    # a helper instead
    line = model.OrderLine(orderid, sku, qty)
    with uow:
        batches = uow.batches.list()
        for batch in batches:
            if line in batch._allocations:
                batch.deallocate(line)
                uow.commit()
                return batch.reference
        else:
            raise model.OrderNotFound(
                f"Could not find an allocation for line {line.orderid}"
            )
