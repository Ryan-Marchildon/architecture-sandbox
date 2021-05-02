import pytest

from src.allocation.domain import model
from src.allocation.adapters.repository import FakeRepository
from src.allocation.service_layer import services


class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


def test_returns_allocation():
    repo = FakeRepository.for_batch("b1", "SHIFTY-LAMP", 100, eta=None)
    result = services.allocate("o1", "SHIFTY-LAMP", 10, repo, FakeSession())
    assert result == "b1"


def test_error_for_invalid_sku():
    repo = FakeRepository.for_batch("b1", "A-REAL-SKU", 100, eta=None)
    with pytest.raises(services.InvalidSku, match="Invalid sku NONEXISTENT-SKU"):
        services.allocate("o1", "NONEXISTENT-SKU", 10, repo, FakeSession())


def test_commits():
    repo = FakeRepository.for_batch("b1", "SHINY-MIRROR", 100, eta=None)
    session = FakeSession()
    services.allocate("o1", "SHINY-MIRROR", 10, repo, session)
    assert session.committed is True


def test_add_batch():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "DELICIOUS-ARMCHAIR", 100, None, repo, session)
    assert repo.get("b1") is not None
    assert session.committed


def test_deallocate_adjusts_available_quantity():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, repo, session)
    services.allocate("o1", "BLUE-PLINTH", 10, repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90

    services.deallocate("o1", "BLUE-PLINTH", 10, repo, session)
    assert batch.available_quantity == 100


def test_deallocate_results_in_correct_quantity():
    repo, session = FakeRepository([]), FakeSession()
    services.add_batch("b1", "BLUE-PLINTH", 100, None, repo, session)
    services.allocate("o1", "BLUE-PLINTH", 10, repo, session)
    services.allocate("o2", "BLUE-PLINTH", 30, repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 60

    services.deallocate("o2", "BLUE-PLINTH", 30, repo, session)
    assert batch.available_quantity == 90


def test_trying_to_deallocate_unallocated_batch():
    repo, session = FakeRepository([]), FakeSession()
    with pytest.raises(model.OrderNotFound):
        services.deallocate("o1", "BLUE-PLINTH", 10, repo, session)
