from flask import Flask, jsonify, request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src import config, model, orm, repository

orm.start_mappers()
get_session = sessionmaker(bind=create_engine(config.get_postgres_uri()))

app = Flask(__name__)


@app.route("/allocate", methods=["POST"])
def allocate_endpoint():
    session = get_session()
    batches = repository.SqlAlchemyRepository(session).list()
    line = model.Orderline(
        request.json["orderid"],
        request.json["sku"],
        request.json["qty"],
    )

    batchref = model.allocate(line, batches)

    return jsonify({"batchref": batchref}), 201


if __name__ == "__main__":
    app.run(debug=True, port=80)