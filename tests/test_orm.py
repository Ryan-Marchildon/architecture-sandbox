import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, mapper

from webservice.src import model
from webservice.src.orm import metadata, order_lines


@pytest.fixture(scope="session")
def in_memory_db():
    engine = create_engine("sqlite:///:memory:", echo=True)  # in-memory DB for dev
    metadata.create_all(engine)
    mapper(model.OrderLine, order_lines)
    return engine


@pytest.fixture()
def session(in_memory_db):
    session = sessionmaker(bind=in_memory_db)()
    yield session
    session.rollback()


def test_orderline_mapper_can_load_lines(session):
    session.execute(
        "INSERT INTO order_lines (orderid, sku, qty) VALUES "
        '("order1", "RED-CHAIR", 12),'
        '("order1", "RED-TABLE", 13),'
        '("order2", "BLUE-LIPSTICK", 14)'
    )
    expected = [
        model.OrderLine("order1", "RED-CHAIR", 12),
        model.OrderLine("order1", "RED-TABLE", 13),
        model.OrderLine("order2", "BLUE-LIPSTICK", 14),
    ]
    assert session.query(model.OrderLine).all() == expected


def test_orderline_mapper_can_save_lines(session):
    new_line = model.OrderLine("order1", "DECORATIVE-WIDGET", 12)
    session.add(new_line)
    session.commit()

    rows = list(session.execute('SELECT orderid, sku, qty FROM "order_lines"'))
    assert rows == [("order1", "DECORATIVE-WIDGET", 12)]