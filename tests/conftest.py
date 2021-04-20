import time

import pytest
import requests
from requests.exceptions import ConnectionError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers

from src.orm import metadata, start_mappers
from src import config


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)()
    clear_mappers()


@pytest.fixture
def add_stock(session):

    # NOTE: we use 'yield' to specify teardown code without callbacks.
    # This is a feature of pytest fixtures, see:
    # https://docs.pytest.org/en/stable/fixture.html#teardown-cleanup-aka-fixture-finalization

    batches_added = set()
    skus_added = set()

    def _add_stock(lines):
        for ref, sku, qty, eta in lines:
            session.execute(
                "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
                " VALUES (:ref, :sku, :qty, :eta)",
                dict(ref=ref, sku=sku, qty=qty, eta=eta),
            )
            batch_id = session.execute(
                "SELECT id FROM batches WHERE reference=:ref AND sku=:sku",
                dict(ref=ref, sku=sku),
            )[0][0]
            batches_added.add(batch_id)
            skus_added.add(sku)
        session.commit()

    yield _add_stock  # NOTE: yields from fixtures produce only one value (will not iterate)

    # this teardown code runs after the test has finished (yield is 'finalized')
    for batch_id in batches_added:
        session.execute(
            "DELETE FROM allocations WHERE batch_id=:batch_id",
            dict(batch_id=batch_id),
        )
        session.execute(
            "DELETE FROM batches WHERE id=:batch_id",
            dict(batch_id=batch_id),
        )
    for sku in skus_added:
        session.execute(
            "DELETE FROM order_lines WHERE sku=:sku",
            dict(sku=sku),
        )
    session.commit()


def wait_for_webapp_spinup():
    deadline = time.time() + 10
    url = config.get_api_url()
    while time.time() < deadline:
        try:
            return requests.get(url)
        except ConnectionError:
            time.sleep(0.5)
    pytest.fail("API never spun up")


@pytest.fixture
def restart_api():
    # TODO: add shell command to start flask
    wait_for_webapp_spinup()