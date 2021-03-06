from datetime import datetime

from flask import Flask, jsonify, request

from src.allocation.domain import commands
from src.allocation.adapters import orm
from src.allocation.service_layer import handlers, messagebus, unit_of_work

orm.start_mappers()

app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    try:
        cmd = commands.Allocate(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(cmd, uow)
        batchref = results.pop(0)
    except handlers.InvalidSku as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"batchref": batchref}), 201


@app.route("/deallocate", methods=["POST"])
def deallocate_endpoint():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    try:
        cmd = commands.Deallocate(
            request.json["orderid"], request.json["sku"], request.json["qty"]
        )
        results = messagebus.handle(cmd, uow)
        batchref = results.pop(0)

    except handlers.InvalidSku as e:
        return jsonify({"message": str(e)}), 400

    return jsonify({"batchref": batchref}), 201


@app.route("/add_batch", methods=["POST"])
def add_batch():
    uow = unit_of_work.SqlAlchemyUnitOfWork()
    eta = request.json["eta"]
    if eta is not None:
        eta = datetime.fromisoformat(eta).date()

    cmd = commands.CreateBatch(
        request.json["ref"], request.json["sku"], request.json["qty"], eta
    )
    messagebus.handle(cmd, uow)

    return "OK", 201


if __name__ == "__main__":
    app.run(debug=True, port=80)