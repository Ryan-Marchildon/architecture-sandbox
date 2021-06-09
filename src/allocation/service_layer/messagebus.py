from src.allocation.domain.model import OutOfStock
from typing import Dict, Type, List, Callable, Union

from tenacity import Retrying, RetryError, stop_after_attempt, wait_exponential

from src.utils.logger import log
from src.allocation.domain import commands, events
from src.allocation.service_layer import handlers, unit_of_work


Message = Union[commands.Command, events.Event]


def handle(message: Message, uow: unit_of_work.AbstractUnitOfWork) -> list:

    results = []
    queue = [message]
    while queue:
        message = queue.pop(0)
        if isinstance(message, events.Event):
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            cmd_result = handle_command(message, queue, uow)
            results.append(cmd_result)
        else:
            raise Exception(f"{message} was not an Event or Command")

    return results


def handle_event(
    event: events.Event, queue: List[Message], uow: unit_of_work.AbstractUnitOfWork
):
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            for attempt in Retrying(
                stop=stop_after_attempt(3), wait=wait_exponential()
            ):
                with attempt:
                    log.debug(f"handling event {event} with handler {handler}")
                    handler(event, uow=uow)
                    queue.extend(uow.collect_new_events())
        except RetryError as retry_failure:
            log.error(
                "Failed to handle event %s times, giving up!",
                retry_failure.last_attempt.attempt_number,
            )
            continue


def handle_command(
    command: commands.Command,
    queue: List[Message],
    uow: unit_of_work.AbstractUnitOfWork,
):
    log.debug(f"handling command {command}")
    try:
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(command, uow=uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception:
        log.exception(f"Exception handling command {command}")
        raise


EVENT_HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
    events.Allocated: [handlers.publish_allocation_event],
}  # type: Dict[Type[events.Event], List[Callable]]


COMMAND_HANDLERS = {
    commands.Allocate: handlers.allocate,
    commands.Deallocate: handlers.deallocate,
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
}  # type: Dict[Type[commands.Command], Callable]
