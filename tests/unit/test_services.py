import pytest

from src.allocation.domain import model
from src.allocation.adapters.repository import FakeRepository
from src.allocation.service_layer import services


class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


def test_returns_allocation():
    line = model.OrderLine("o1", "SHIFTY-LAMP", 10)
    batch = model.Batch("b1", "SHIFTY-LAMP", 100, eta=None)
    repo = FakeRepository([batch])

    result = services.allocate(line, repo, FakeSession())
    assert result == "b1"


def test_error_for_invalid_sku():
    line = model.OrderLine("o1", "NONEXISTENT-SKU", 10)
    batch = model.Batch("b1", "A-REAL-SKU", 100, eta=None)
    repo = FakeRepository([batch])

    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENT-SKU"):
        services.allocate(line, repo, FakeSession())


def test_commits():
    line = model.OrderLine("o1", "SHINY-MIRROR", 10)
    batch = model.Batch("b1", "SHINY-MIRROR", 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    services.allocate(line, repo, session)
    assert session.committed is True


def test_deallocate_adjusts_available_quantity():
    repo, session = FakeRepository([]), FakeSession()
    staged_batch = model.Batch("b1", "BLUE-PLINTH", 100, None)
    line = model.OrderLine("o1", "BLUE-PLINTH", 10)
    services.add_batch(staged_batch, repo, session)
    services.allocate(line, repo, session)

    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90

    services.deallocate(line, repo, session)
    assert batch.available_quantity == 100


def test_deallocate_results_in_correct_quantity():
    repo, session = FakeRepository([]), FakeSession()
    staged_batch = model.Batch("b1", "BLUE-PLINTH", 100, None)
    line_1 = model.OrderLine("o1", "BLUE-PLINTH", 10)
    line_2 = model.OrderLine("o2", "BLUE-PLINTH", 30)
    services.add_batch(staged_batch, repo, session)
    services.allocate(line_1, repo, session)
    services.allocate(line_2, repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 60

    services.deallocate(line_2, repo, session)
    assert batch.available_quantity == 90


def test_trying_to_deallocate_unallocated_batch():
    repo, session = FakeRepository([]), FakeSession()
    line = model.OrderLine("o1", "BLUE-PLINTH", 10)

    with pytest.raises(model.OrderNotFound):
        services.deallocate(line, repo, session)
