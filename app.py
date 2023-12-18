#!/usr/bin/env python
import os
from flask import Flask, jsonify, Response, request
import xml.etree.ElementTree as ET

from db.models import db, Student, init_db

app = Flask(__name__)
init_db(app)


@app.route("/")
def hello() -> Response:
    user = Student(fname="test_user1", lname="test_last")
    print("\n\n hello in endpoint")

    db.session.add(user)
    db.session.commit()

    return "<h1>hello there</h1>"


@app.route("/import", methods=["POST"])
def import_xml() -> Response:
    root = ET.fromstring(request.data)
    resp = {"root": "hello"}

    return jsonify(resp)


@app.route("/results/<test_id>/aggregate", methods=["GET"])
def aggregate_test_results(test_id: str) -> Response:
    resp = {"test id": test_id}
    return jsonify(resp)


if __name__ == "__main__":
    init_db()
    with app.app_context():
        db.create_all()
    app.run()
