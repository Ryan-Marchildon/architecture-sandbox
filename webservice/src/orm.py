from sqlalchemy import MetaData, Table, Column, Integer, String

from webservice.src import model


metadata = MetaData()

# define domain object schemas
order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
    Column("orderid", String(255)),
)