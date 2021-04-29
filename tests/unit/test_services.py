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
