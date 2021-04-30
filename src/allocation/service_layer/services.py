from typing import Optional
from datetime import date

from src.utils.logger import log
from src.allocation.domain import model
from src.allocation.adapters.repository import AbstractRepository


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {batch.sku for batch in batches}


def add_batch(batch: model.Batch, repo: AbstractRepository, session):
    repo.add(batch)
    session.commit()


def allocate(line: model.OrderLine, repo: AbstractRepository, session) -> str:
    batches = repo.list()
    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku {line.sku}")
    batchref = model.allocate(line, batches)
    session.commit()
    return batchref


def deallocate(line: model.OrderLine, repo: AbstractRepository, session):
    # to scale, this would best be done by querying the allocations
    # table directly, but since we lack it in the repo, we'll use
    # a helper instead
    batches = repo.list()
    for batch in batches:
        if line in batch._allocations:
            batch.deallocate(line)
            session.commit()
            return batch.reference
    else:
        raise model.OrderNotFound(
            f"Could not find an allocation for line {line.orderid}"
        )
