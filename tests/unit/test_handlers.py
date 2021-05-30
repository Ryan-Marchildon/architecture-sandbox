from datetime import date

import pytest

from src.allocation.domain import model, events
from src.allocation.adapters.repository import FakeRepository
from src.allocation.service_layer import handlers, messagebus
from src.allocation.service_layer.unit_of_work import FakeUnitOfWork


class TestAddBatch:
    @staticmethod
    def test_add_batch_for_new_product():
        uow = FakeUnitOfWork()
        messagebus.handle(
            [events.BatchCreated("b1", "DELICIOUS-ARMCHAIR", 100, None)], uow
        )
        assert uow.products.get("DELICIOUS-ARMCHAIR") is not None
        assert uow.committed

    @staticmethod
    def test_add_batch_for_existing_product():
        uow = FakeUnitOfWork()
        messagebus.handle(
            [
                events.BatchCreated("b1", "GARISH-RUG", 100, None),
                events.BatchCreated("b2", "GARISH-RUG", 99, None),
            ],
            uow,
        )
        assert "b2" in [b.reference for b in uow.products.get("GARISH-RUG").batches]


class TestAllocate:
    @staticmethod
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

    @staticmethod
    def test_allocate_errors_for_invalid_sku():
        uow = FakeUnitOfWork()
        messagebus.handle([events.BatchCreated("b1", "A-REAL-SKU", 100, None)], uow)

        with pytest.raises(handlers.InvalidSku, match="Invalid sku NONEXISTENT-SKU"):
            messagebus.handle(
                [events.AllocationRequest("o1", "NONEXISTENT-SKU", 10)], uow
            )

    @staticmethod
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


class TestDeallocate:
    @staticmethod
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
            filter(
                lambda b: b.reference == "b1", uow.products.get("BLUE-PLINTH").batches
            ),
            None,
        )
        assert batch.available_quantity == 90

        messagebus.handle([events.DeallocationRequest("o1", "BLUE-PLINTH", 10)], uow)
        assert batch.available_quantity == 100

    @staticmethod
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
            filter(
                lambda b: b.reference == "b1", uow.products.get("BLUE-PLINTH").batches
            ),
            None,
        )
        assert batch.available_quantity == 60

        messagebus.handle([events.DeallocationRequest("o2", "BLUE-PLINTH", 30)], uow)
        assert batch.available_quantity == 90

    @staticmethod
    def test_trying_to_deallocate_unallocated_batch():
        uow = FakeUnitOfWork()
        messagebus.handle(events.BatchCreated("b1", "BLUE-PLINTH", 100, None), uow)

        with pytest.raises(model.OrderNotFound):
            messagebus.handle(
                [events.DeallocationRequest("o1", "BLUE-PLINTH", 10)], uow
            )


class TestChangeBatchQuantity:
    @staticmethod
    def test_changes_available_quantity():
        uow = FakeUnitOfWork()
        messagebus.handle(
            events.BatchCreated("batch1", "ADORABLE-STOOL", 100, None), uow
        )
        [batch] = uow.products.get(sku="ADORABLE-STOOL").batches
        assert batch.available_quantity == 100

        messagebus.handle(events.BatchQuantityChanged("batch1", 50), uow)
        assert batch.available_quantity == 50

    @staticmethod
    def test_reallocates_if_necessary():
        uow = FakeUnitOfWork()
        event_history = [
            events.BatchCreated("batch1", "INDIFFERENT-TABLE", 50, None),
            events.BatchCreated("batch2", "INDIFFERENT-TABLE", 50, date.today()),
            events.AllocationRequest("order1", "INDIFFERENT-TABLE", 20),
            events.AllocationRequest("order2", "INDIFFERENT-TABLE", 20),
        ]
        for e in event_history:
            messagebus.handle(e, uow)
        [batch1, batch2] = uow.products.get(sku="INDIFFERENT-TABLE").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        messagebus.handle(events.BatchQuantityChanged("batch1", 25), uow)

        # order 1 or order 2 will be de-allocated, so we will have 25 - 20
        assert batch1.available_quantity == 5
        # and 20 will be re-allocated to the next batch
        assert batch2.available_quantity == 30
