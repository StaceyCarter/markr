#!/usr/bin/env python
import os
from flask import Flask, jsonify, Response, request, abort
import xml.etree.ElementTree as ET

from markr.db.models import db, Student, init_db, extract_data, get_test_score_summary

_EXPECTED_DOC_TAG: str = "mcq-test-results"

app = Flask(__name__)
init_db(app)


@app.route("/")
def hello() -> Response:

    return "<h1>hello there</h1>"


@app.route("/import", methods=["POST"])
def import_xml() -> Response:
    """
    """
    if request.content_type != 'text/xml+markr':
        abort(400, "content_type must be text/xml+markr")

    root = ""
    try: 
        root = ET.fromstring(request.data)
    except ET.ParseError: 
        abort(400, "Unable to read XML")
    
    if root.tag != _EXPECTED_DOC_TAG:
        abort(400, "Unexpected XML format")

    resp = {"root": "hello"}
    
    try:
        extract_data(root)
    except RuntimeError as e: 
        abort(400, "Error extracting test data: {e}")

    return jsonify(resp)


@app.route("/results/<test_id>/aggregate", methods=["GET"])
def aggregate_test_results(test_id: str) -> Response:
    try: 
        test_id = int(test_id)
    except ValueError:
        abort(400, "Invalid test id supplied. Must be an integer")
    
    try:
        resp = get_test_score_summary(int(test_id))
    except RuntimeError as e: 
        abort(400, f"Unable to retrieve score summary. Error: {e}")

    return jsonify(resp)


