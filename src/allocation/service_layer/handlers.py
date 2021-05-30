from typing import Optional
from datetime import date

from src.utils.logger import log
from src.allocation.domain import model, events
from src.allocation.service_layer import unit_of_work


class InvalidSku(Exception):
    pass


class email:
    """
    Quick mock of an email service.
    """

    @staticmethod
    def send_email(email_domain, email_msg):
        pass


def is_valid_sku(sku, batches):
    return sku in {batch.sku for batch in batches}


def send_out_of_stock_notification(
    event: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork
):
    email.send_email(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


def add_batch(
    event: events.BatchCreated,
    uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            product = model.Product(event.sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(event.ref, event.sku, event.qty, event.eta))
        uow.commit()


def allocate(
    event: events.AllocationRequest, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = model.OrderLine(event.orderid, event.sku, event.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")
        batchref = product.allocate(line)
        uow.commit()
        return batchref


def deallocate(event: events.DeallocationRequest, uow: unit_of_work.AbstractUnitOfWork):
    line = model.OrderLine(event.orderid, event.sku, event.qty)
    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku {line.sku}")

        for batch in product.batches:
            if line in batch._allocations:
                batch.deallocate(line)
                uow.commit()
                return batch.reference
        else:
            raise model.OrderNotFound(
                f"Could not find an allocation for line {line.orderid}"
            )


def change_batch_quantity(
    event: events.BatchQuantityChanged, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        product = uow.products.get_by_batchref(batchref=event.ref)
        product.change_batch_quantity(ref=event.ref, qty=event.qty)
        uow.commit()