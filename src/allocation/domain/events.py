from typing import Optional, List, Set
from datetime import date

from dataclasses import dataclass


class Event:
    pass


@dataclass
class OutOfStock(Event):
    sku: str
