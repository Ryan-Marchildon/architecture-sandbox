from datetime import datetime

from flask import Flask, jsonify, request

from src.allocation import config
from src.allocation.domain import model, events
from src.allocation.adapters import orm
from src.allocation.service_layer import handlers, messagebus, unit_of_work

orm.start_mappers()

app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    try:
        event = events.AllocationRequest(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(event, uow)
        batchref = results.pop(0)
    except handlers.InvalidSku as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"batchref": batchref}), 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    try:
        event = events.DeallocationRequest(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(event, uow)
        batchref = results.pop(0)

    except handlers.InvalidSku as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"batchref": batchref}), 201


@app.route("/batches", methods=["POST"])
def add_batch():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    event = events.BatchCreated(
        request.json["ref"], request.json["sku"], request.json["qty"], eta
    )
    messagebus.handle(event, uow)

    return "OK", 201


if __name__ == "__main__":
    app.run(debug=True, port=80)