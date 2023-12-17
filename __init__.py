from flask import Flask, jsonify, Response, request
import xml.etree.ElementTree as ET

app = Flask(__name__)

@app.route('/')
def hello():
    return '<h1>Hello, World!</h1>'

@app.route('/import', methods=["POST"])
def import_xml() -> Response:
    root = ET.fromstring(request.data)
    resp = {
        "root" : "hello"
    }
    return jsonify(resp) 

@app.route('/results/<test_id>/aggregate', methods=["GET"])
def aggregate_test_results(test_id: str) -> Response:
    resp = {
        "test id" : test_id
    }
    return jsonify(resp) 

