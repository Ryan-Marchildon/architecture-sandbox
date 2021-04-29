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
def test_api_returns_allocation(add_stock):
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
