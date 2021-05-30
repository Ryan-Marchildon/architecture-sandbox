from typing import Dict, Type, List, Callable, Union

from src.allocation.domain import events
from src.allocation.service_layer import handlers, unit_of_work


def handle(
    event: Union[events.Event, List[events.Event]], uow: unit_of_work.AbstractUnitOfWork
) -> list:
    if isinstance(event, List):
        queue = event
    else:
        queue = [event]

    results = []
    while queue:
        event = queue.pop(0)
        for handler in HANDLERS[type(event)]:
            results.append(handler(event, uow=uow))
            queue.extend(uow.collect_new_events())

    return results


HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
    events.BatchCreated: [handlers.add_batch],
    events.AllocationRequest: [handlers.allocate],
    events.DeallocationRequest: [handlers.deallocate],
    events.BatchQuantityChanged: [handlers.change_batch_quantity],
}  # type: Dict[Type[events.Event], List[Callable]]
