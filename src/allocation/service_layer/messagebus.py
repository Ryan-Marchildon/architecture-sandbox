from typing import Dict, Type, List, Callable

from src.allocation.domain import events


class email:
    """
    Quick mock of an email service.
    """

    @staticmethod
    def send_email(email_domain, email_msg):
        pass


def handle(event: events.Event):
    for handler in HANDLERS[type(event)]:
        handler(event)


def send_out_of_stock_notification(event: events.OutOfStock):
    email.send_email(
        "stock@made.com",
        f"Out of stock for {event.sku}",
    )


HANDLERS = {
    events.OutOfStock: [send_out_of_stock_notification]
}  # type: Dict[Type[events.Event], List[Callable]]
