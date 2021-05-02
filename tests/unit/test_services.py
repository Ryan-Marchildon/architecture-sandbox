import pytest

from src.allocation.domain import model
from src.allocation.adapters.repository import FakeRepository
from src.allocation.service_layer import services, unit_of_work


class FakeUnitOfWork(unit_of_work.AbstractUnitOfWork):
    def __init__(self):
        self.batches = FakeRepository([])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_add_batch():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "DELICIOUS-ARMCHAIR", 100, None, uow)
    assert uow.batches.get("b1") is not None
    assert uow.committed


def test_returns_allocation():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "SHIFTY-LAMP", 100, None, uow)
    result = services.allocate("o1", "SHIFTY-LAMP", 10, uow)
    assert result == "b1"


def test_error_for_invalid_sku():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "A-REAL-SKU", 100, None, uow)
    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENT-SKU"):
        services.allocate("o1", "NONEXISTENT-SKU", 10, uow)


def test_commits():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "SHINY-MIRROR", 100, None, uow)
    services.allocate("o1", "SHINY-MIRROR", 10, uow)
    assert uow.committed is True


def test_deallocate_adjusts_available_quantity():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, uow)
    services.allocate("o1", "BLUE-PLINTH", 10, uow)
    batch = uow.batches.get(reference="b1")
    assert batch.available_quantity == 90

    services.deallocate("o1", "BLUE-PLINTH", 10, uow)
    assert batch.available_quantity == 100


def test_deallocate_results_in_correct_quantity():
    uow = FakeUnitOfWork()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, uow)
    services.allocate("o1", "BLUE-PLINTH", 10, uow)
    services.allocate("o2", "BLUE-PLINTH", 30, uow)
    batch = uow.batches.get(reference="b1")
    assert batch.available_quantity == 60

    services.deallocate("o2", "BLUE-PLINTH", 30, uow)
    assert batch.available_quantity == 90


def test_trying_to_deallocate_unallocated_batch():
    uow = FakeUnitOfWork()
    with pytest.raises(model.OrderNotFound):
        services.deallocate("o1", "BLUE-PLINTH", 10, uow)
