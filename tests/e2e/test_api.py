from uuid import uuid4
import pytest

from tests.random_refs import random_batchref, random_orderid, random_sku
from tests.e2e import api_client


# NOTE: usefixtures() lets us run a fixture even if we don't need
# this fixture object within our test function
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_201_and_allocated_batch():
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)
    api_client.post_to_add_batch(laterbatch, sku, 100, "2011-01-02")
    api_client.post_to_add_batch(earlybatch, sku, 100, "2011-01-01")
    api_client.post_to_add_batch(otherbatch, othersku, 100, None)

    r = api_client.post_to_allocate(random_orderid(), sku, 3, expect_success=True)
    assert r.status_code == 201
    assert r.json()["batchref"] == earlybatch


@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku, orderid = random_sku(), random_orderid()

    r = api_client.post_to_allocate(orderid, unknown_sku, 20, expect_success=False)
    assert r.status_code == 400
    assert r.json()["message"] == f"Invalid sku {unknown_sku}"


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_deallocate():
    sku, order1, order2 = random_sku(), random_orderid(), random_orderid()
    batch = random_batchref()
    api_client.post_to_add_batch(batch, sku, 100, "2011-01-02")

    # fully allocate
    r = api_client.post_to_allocate(order1, sku, 100, expect_success=True)
    assert r.json()["batchref"] == batch

    # cannot allocate second order
    r = api_client.post_to_allocate(order2, sku, 100, expect_success=False)
    assert r.status_code == 201
    assert r.json()["batchref"] == None  # tells us it was not allocated

    # deallocate
    r = api_client.post_to_deallocate(order1, sku, 100, expect_success=True)
    assert r.ok

    # now we can allocate second order
    r = api_client.post_to_allocate(order2, sku, 100, expect_success=True)
    assert r.ok
    assert r.json()["batchref"] == batch