from uuid import uuid4
import pytest
import requests

from src.allocation import config


def random_suffix():
    return uuid4()


def create_tag(name=None):
    tag = "" if not name else f"{name}-"
    return tag


def random_sku(name=None):
    return f"sku-{create_tag(name)}{random_suffix()}"


def random_batchref(name=None):
    return f"batch-{create_tag(name)}{random_suffix()}"


def random_orderid(name=None):
    return f"order-{create_tag(name)}{random_suffix()}"


# NOTE: usefixtures() lets us run a fixture even if we don't need
# this fixture object within our test function
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_201_and_allocated_batch(add_stock):
    sku, othersku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)
    add_stock(
        [
            (laterbatch, sku, 100, "2011-01-02"),
            (earlybatch, sku, 100, "2011-01-01"),
            (otherbatch, othersku, 100, None),
        ]
    )
    data = {"orderid": random_orderid(), "sku": sku, "qty": 3}
    url = config.get_api_url()
    r = requests.post(f"{url}/allocate", json=data)
    assert r.status_code == 201
    assert r.json()["batchref"] == earlybatch


@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku, orderid = random_sku(), random_orderid()
    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    url = config.get_api_url()
    r = requests.post(f"{url}/allocate", json=data)
    assert r.status_code == 400
    assert r.json()["message"] == f"Invalid sku {unknown_sku}"


def post_to_add_batch(batch, sku, qty, eta):
    pass


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_deallocate(add_stock):
    sku, order1, order2 = random_sku(), random_orderid(), random_orderid()
    batch = random_batchref()
    add_stock([(batch, sku, 100, "2011-01-02")])

    url = config.get_api_url()
    # fully allocate
    r = requests.post(
        f"{url}/allocate", json={"orderid": order1, "sku": sku, "qty": 100}
    )
    assert r.json()["batchref"] == batch

    # cannot allocate second order
    r = requests.post(
        f"{url}/allocate", json={"orderid": order2, "sku": sku, "qty": 100}
    )
    assert r.status_code == 400

    # deallocate
    r = requests.post(
        f"{url}/deallocate",
        json={
            "orderid": order1,
            "sku": sku,
            "qty": 100,
        },
    )
    assert r.ok

    # now we can allocate second order
    r = requests.post(
        f"{url}/allocate", json={"orderid": order2, "sku": sku, "qty": 100}
    )
    assert r.ok
    assert r.json()["batchref"] == batch