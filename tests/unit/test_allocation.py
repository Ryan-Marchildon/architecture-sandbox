import pytest
from datetime import date, timedelta

from src.utils.logger import log
from src.allocation.domain.model import (
    Batch,
    OrderLine,
    allocate,
    OutOfStock,
    OrderNotFound,
)


@pytest.fixture()
def tomorrow():
    return date.today() + timedelta(days=1)


@pytest.fixture()
def next_week():
    return date.today() + timedelta(days=7)


def make_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, eta=date.today()),
        OrderLine("order-123", sku, line_qty),
    )


class TestAllocationServices:
    def test_prefers_current_stock_batches_to_shipments(self, tomorrow):
        in_stock_batch = Batch("in-stock-batch", "LAVA-LAMP", 100, eta=None)
        shipment_batch = Batch("shipment-batch", "LAVA-LAMP", 100, eta=tomorrow)
        line = OrderLine("oref", "LAVA-LAMP", 10)

        allocate(line, [in_stock_batch, shipment_batch])

        assert in_stock_batch.available_quantity == 90
        assert shipment_batch.available_quantity == 100

    def test_prefers_earlier_batches(self, tomorrow, next_week):
        earliest = Batch("speedy-batch", "SILVER-SPOON", 100, eta=date.today())
        medium = Batch("normal-batch", "SILVER-SPOON", 100, eta=tomorrow)
        latest = Batch("slow-batch", "SILVER-SPOON", 100, eta=next_week)
        line = OrderLine("order1", "SILVER-SPOON", 10)

        allocate(line, [medium, earliest, latest])

        assert earliest.available_quantity == 90
        assert medium.available_quantity == 100
        assert latest.available_quantity == 100

    def test_returns_allocated_batch_ref(self, tomorrow):
        in_stock_batch = Batch("in-stock-batch-ref", "FANCY-CHAIR", 100, eta=None)
        shipment_batch = Batch("shipment-batch-ref", "FANCY-CHAIR", 100, eta=tomorrow)
        line = OrderLine("oref", "FANCY-CHAIR", 10)

        allocation = allocate(line, [in_stock_batch, shipment_batch])

        assert allocation == in_stock_batch.reference

    def test_raises_out_of_stock_exception_if_cannot_allocate(self):
        batch = Batch("batch1", "WOOD-CABINET", 10, eta=date.today())
        allocate(OrderLine("order1", "WOOD-CABINET", 10), [batch])

        with pytest.raises(OutOfStock, match="WOOD-CABINET"):
            allocate(OrderLine("order2", "WOOD-CABINET", 1), [batch])


class TestAllocationObjects:
    def test_allocating_to_a_batch_reduces_the_available_quantity(self):
        batch = Batch(ref="batch-001", sku="SMALL-TABLE", qty=20, eta=date.today())
        line = OrderLine("order-ref", "SMALL-TABLE", 2)

        batch.allocate(line)

        assert batch.available_quantity == 18

    def test_can_allocate_if_available_greater_than_required(self):
        large_batch, small_line = make_batch_and_line("ELEGANT-LAMP", 20, 2)
        assert large_batch.can_allocate(small_line)

    def test_cannot_allocate_if_available_smaller_than_required(self):
        small_batch, large_line = make_batch_and_line("ELEGANT-LAMP", 2, 20)
        assert small_batch.can_allocate(large_line) is False

    def test_can_allocate_if_available_equal_to_required(self):
        batch, line = make_batch_and_line("ELEGANT-LAMP", 2, 2)
        assert batch.can_allocate(line)

    def test_cannot_allocate_if_skus_do_not_match(self):
        batch = Batch("batch-001", "UNCOMFOTABLE-CHAIR", 100, eta=None)
        different_sku_line = OrderLine("order-123", "EXPENSIVE-TOASTER", 10)
        assert batch.can_allocate(different_sku_line) is False

    def test_can_only_deallocate_allocated_lines(self):
        batch, unallocated_line = make_batch_and_line("DECORATIVE-TRINKET", 20, 2)
        try:
            batch.deallocate(unallocated_line)
        except OrderNotFound as e:
            log.info(e)

        assert batch.available_quantity == 20

    def test_allocation_is_idempotent(self):
        batch, line = make_batch_and_line("ANGULAR-DESK", 20, 2)
        batch.allocate(line)
        batch.allocate(line)
        assert batch.available_quantity == 18
