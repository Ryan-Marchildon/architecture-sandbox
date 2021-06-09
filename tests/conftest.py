import time
import shutil
import subprocess
import requests
from requests.exceptions import ConnectionError

import pytest
import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, clear_mappers
from sqlalchemy.exc import OperationalError

from src.allocation.adapters.orm import metadata, start_mappers
from src.allocation import config


@pytest.fixture
def in_memory_db():
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    return engine


@pytest.fixture
def session_factory(in_memory_db):
    start_mappers()
    yield sessionmaker(bind=in_memory_db)
    clear_mappers()


@pytest.fixture
def session(session_factory):
    return session_factory()


def wait_for_postgres_spinup(engine):
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            return engine.connect()
        except OperationalError:
            time.sleep(0.5)
    pytest.fail("Postgres never spun up")


@pytest.fixture(scope="session")
def postgres_db():
    engine = create_engine(config.get_postgres_uri())
    wait_for_postgres_spinup(engine)
    metadata.create_all(engine)
    return engine


@pytest.fixture
def postgres_session_factory(postgres_db):
    start_mappers()
    yield sessionmaker(bind=postgres_db)
    clear_mappers()


@pytest.fixture
def postgres_session(postgres_session_factory):
    return postgres_session_factory()


@pytest.fixture
def add_stock(postgres_session):
    """
    Adds batches to the postgres DB;
    for running e2e tests.

    """

    # NOTE: we use 'yield' to specify teardown code without callbacks.
    # This is a feature of pytest fixtures, see:
    # https://docs.pytest.org/en/stable/fixture.html#teardown-cleanup-aka-fixture-finalization

    batches_added = set()
    skus_added = set()

    def _add_stock(lines):
        for ref, sku, qty, eta in lines:
            postgres_session.execute(
                "INSERT INTO batches (reference, sku, _purchased_quantity, eta)"
                " VALUES (:ref, :sku, :qty, :eta)",
                dict(ref=ref, sku=sku, qty=qty, eta=eta),
            )
            [[batch_id]] = postgres_session.execute(
                "SELECT id FROM batches WHERE reference=:ref AND sku=:sku",
                dict(ref=ref, sku=sku),
            )
            batches_added.add(batch_id)
            skus_added.add(sku)
        postgres_session.commit()

    yield _add_stock  # NOTE: yields from fixtures produce only one value (will not iterate)

    # this teardown code runs after the test has finished (yield is 'finalized')
    for batch_id in batches_added:
        postgres_session.execute(
            "DELETE FROM allocations WHERE batch_id=:batch_id",
            dict(batch_id=batch_id),
        )
        postgres_session.execute(
            "DELETE FROM batches WHERE id=:batch_id",
            dict(batch_id=batch_id),
        )
    for sku in skus_added:
        postgres_session.execute(
            "DELETE FROM order_lines WHERE sku=:sku",
            dict(sku=sku),
        )
    postgres_session.commit()


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


def wait_for_redis_spinup():
    deadline = time.time() + 10
    while time.time() < deadline:
        try:
            r = redis.Redis(**config.get_redis_host_and_port())
            return r.ping()
        except OperationalError:
            time.sleep(0.5)
    pytest.fail("Redis never spun up")


@pytest.fixture
def restart_redis_pubsub():
    wait_for_redis_spinup()
    if not shutil.which("docker-compose"):
        print("skipping restart, assumes running in container")
        return
    subprocess.run(
        ["docker-compose", "restart", "-t", "0", "redis_pubsub"],
        check=True,
    )
