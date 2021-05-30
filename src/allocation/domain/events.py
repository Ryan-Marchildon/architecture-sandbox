from typing import Optional, List, Set
from datetime import date

from dataclasses import dataclass


class Event:
    pass


@dataclass
class OutOfStock(Event):
    sku: str


@dataclass
class BatchCreated(Event):
    ref: str
    sku: str
    qty: int
    eta: Optional[date] = None


@dataclass
class AllocationRequest(Event):
    orderid: str
    sku: str
    qty: int


@dataclass
class DeallocationRequest(Event):
    orderid: str
    sku: str
    qty: int
