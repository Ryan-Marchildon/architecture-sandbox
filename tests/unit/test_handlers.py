import pytest

from src.allocation.domain import model, events
from src.allocation.adapters.repository import FakeRepository
from src.allocation.service_layer import handlers, messagebus
from src.allocation.service_layer.unit_of_work import FakeUnitOfWork


def test_add_batch_for_new_product():
    uow = FakeUnitOfWork()
    messagebus.handle([events.BatchCreated("b1", "DELICIOUS-ARMCHAIR", 100, None)], uow)
    assert uow.products.get("DELICIOUS-ARMCHAIR") is not None
    assert uow.committed


def test_add_batch_for_existing_product():
    uow = FakeUnitOfWork()
    messagebus.handle(
        [
            events.BatchCreated("b1", "GARISH-RUG", 100, None, uow),
            events.BatchCreated("b2", "GARISH-RUG", 99, None, uow),
        ],
        uow,
    )
    assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


def test_allocate_returns_allocation():
    uow = FakeUnitOfWork()

    results = messagebus.handle(
        [
            events.BatchCreated("b1", "SHIFTY-LAMP", 100, None),
            events.AllocationRequest("o1", "SHIFTY-LAMP", 10),
        ],
        uow,
    )
    assert results.pop() == "b1"


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    messagebus.handle([events.BatchCreated("b1", "A-REAL-SKU", 100, None)], uow)

    with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENT-SKU"):
        messagebus.handle([events.AllocationRequest("o1", "NONEXISTENT-SKU", 10)], uow)


def test_allocate_commits():
    uow = FakeUnitOfWork()
    messagebus.handle(
        [
            events.BatchCreated("b1", "SHINY-MIRROR", 100, None),
            events.AllocationRequest("o1", "SHINY-MIRROR", 10),
        ],
        uow,
    )
    assert uow.committed is True


def test_deallocate_adjusts_available_quantity():
    uow = FakeUnitOfWork()
    messagebus.handle(
        [
            events.BatchCreated("b1", "BLUE-PLINTH", 100, None),
            events.AllocationRequest("o1", "BLUE-PLINTH", 10),
        ],
        uow,
    )
    batch = next(
        filter(lambda b: b.reference == "b1", uow.products.get("BLUE-PLINTH").batches),
        None,
    )
    assert batch.available_quantity == 90

    messagebus.handle([events.DeallocationRequest("o1", "BLUE-PLINTH", 10)], uow)
    assert batch.available_quantity == 100


def test_deallocate_results_in_correct_quantity():
    uow = FakeUnitOfWork()

    messagebus.handle(
        [
            events.BatchCreated("b1", "BLUE-PLINTH", 100, None),
            events.AllocationRequest("o1", "BLUE-PLINTH", 10),
            events.AllocationRequest("o2", "BLUE-PLINTH", 30),
        ],
        uow,
    )

    batch = next(
        filter(lambda b: b.reference == "b1", uow.products.get("BLUE-PLINTH").batches),
        None,
    )
    assert batch.available_quantity == 60

    messagebus.handle([events.DeallocationRequest("o2", "BLUE-PLINTH", 30)], uow)
    assert batch.available_quantity == 90


def test_trying_to_deallocate_unallocated_batch():
    uow = FakeUnitOfWork()
    messagebus.handle([events.BatchCreated("b1", "BLUE-PLINTH", 100, None)], uow)

    with pytest.raises(model.OrderNotFound):
        messagebus.handle([events.DeallocationRequest("o1", "BLUE-PLINTH", 10)], uow)
