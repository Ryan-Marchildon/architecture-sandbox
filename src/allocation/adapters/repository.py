import abc
from typing import Set

from src.allocation.domain import model


class AbstractProductRepository(abc.ABC):
    def __init__(self):
        self.seen = set()  # type: Set[model.Product]

    def add(self, product: model.Product):
        self._add(product)
        self.seen.add(product)  # note this is Set.add()

    def get(self, sku) -> model.Product:
        product = self._get(sku)
        if product:
            self.seen.add(product)
        return product

    @abc.abstractmethod
    def _add(self, product: model.Product):
        raise NotImplementedError

    @abc.abstractmethod
    def _get(self, sku) -> model.Product:
        raise NotImplementedError

    @abc.abstractmethod
    def list(self):
        raise NotImplementedError


class SqlAlchemyRepository(AbstractProductRepository):
    def __init__(self, session):
        super().__init__()
        self.session = session

    def _add(self, product: model.Product):
        self.session.add(product)

    def _get(self, sku: str):
        return self.session.query(model.Product).filter_by(sku=sku).first()

    def list(self):
        return self.session.query(model.Product).all()


# for mocks during tests
class FakeRepository(AbstractProductRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set(products)

    def _add(self, product):
        self._products.add(product)

    def _get(self, sku: str):
        return next((p for p in self._products if p.sku == sku), None)

    def list(self):
        return list(self._products)

    # fixtures for keeping all of our tests' domain-model dependencies,
    # so we can keep those dependencies decoupled from our test definitions
    @staticmethod
    def for_product(sku, batches, version_number):
        return FakeRepository([model.Product(sku, batches, version_number)])
