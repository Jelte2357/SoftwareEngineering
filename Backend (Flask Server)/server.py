import random

from flask import Flask, jsonify, request
import time

app = Flask(__name__)


@app.post("/")
def generate_numbers():
    time.sleep(0)  # Simulate some processing time
    data = request.get_json(silent=True) or {}
    return jsonify({uuid: random.uniform(0.1, 0.9) for uuid in data}), 200


if __name__ == "__main__":
    app.run(port=4352, debug=True)
