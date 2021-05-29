from typing import Dict, Type, List, Callable

from src.allocation.domain import events
from src.allocation.service_layer import handlers


def handle(event: events.Event):
    for handler in HANDLERS[type(event)]:
        handler(event)


HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification]
}  # type: Dict[Type[events.Event], List[Callable]]
