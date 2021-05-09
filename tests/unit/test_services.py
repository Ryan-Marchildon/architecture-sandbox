import pytest

from src.allocation.domain import model
from src.allocation.adapters.repository import FakeRepository
from src.allocation.service_layer import services
from src.allocation.service_layer.unit_of_work import FakeUnitOfWork


def test_add_batch_for_new_product():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "DELICIOUS-ARMCHAIR", 100, None, uow)
    assert uow.products.get("DELICIOUS-ARMCHAIR") is not None
    assert uow.committed


def test_add_batch_for_existing_product():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "GARISH-RUG", 100, None, uow)
    services.add_batch("b2", "GARISH-RUG", 99, None, uow)
    assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


def test_allocate_returns_allocation():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "SHIFTY-LAMP", 100, None, uow)
    result = services.allocate("o1", "SHIFTY-LAMP", 10, uow)
    assert result == "b1"


def test_allocate_errors_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "A-REAL-SKU", 100, None, uow)
    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENT-SKU"):
        services.allocate("o1", "NONEXISTENT-SKU", 10, uow)


def test_allocate_commits():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "SHINY-MIRROR", 100, None, uow)
    services.allocate("o1", "SHINY-MIRROR", 10, uow)
    assert uow.committed is True


def test_deallocate_adjusts_available_quantity():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, uow)
    services.allocate("o1", "BLUE-PLINTH", 10, uow)
    batch = next(
        filter(lambda b: b.reference == "b1", uow.products.get("BLUE-PLINTH").batches),
        None,
    )
    assert batch.available_quantity == 90

    services.deallocate("o1", "BLUE-PLINTH", 10, uow)
    assert batch.available_quantity == 100


def test_deallocate_results_in_correct_quantity():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, uow)
    services.allocate("o1", "BLUE-PLINTH", 10, uow)
    services.allocate("o2", "BLUE-PLINTH", 30, uow)
    batch = next(
        filter(lambda b: b.reference == "b1", uow.products.get("BLUE-PLINTH").batches),
        None,
    )
    assert batch.available_quantity == 60

    services.deallocate("o2", "BLUE-PLINTH", 30, uow)
    assert batch.available_quantity == 90


def test_trying_to_deallocate_unallocated_batch():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, uow)
    with pytest.raises(model.OrderNotFound):
        services.deallocate("o1", "BLUE-PLINTH", 10, uow)
