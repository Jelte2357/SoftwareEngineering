from flask import Flask, jsonify, request
from predict import HateSpeechPredictor
from config import *


app = Flask(__name__)

app.config["MAX_REQUEST_LENGTH"] = MAX_REQUEST_LENGTH
app.config["MAX_BATCH_SIZE"] = MAX_BATCH_SIZE

classifier = HateSpeechPredictor(
    model_dir=MODEL_DIR,
)
app.extensions["hate_speech_predictor"] = classifier

@app.route("/", methods=["POST"])
def predict_texts():

    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json."
        }), 400

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    if not all(isinstance(x[0], str) and isinstance(x[1], str) for x in payload.items()):
        return jsonify({
            "error": "All keys and values in the JSON object must be strings."
        }), 418
        
    if len(payload) > MAX_REQUEST_LENGTH:
        return jsonify({
            "error": f"Request body must contain at most {MAX_REQUEST_LENGTH} texts."
        }), 413
    

    keys, texts = zip(*payload.items())
    predictions = classifier.predict(texts)
    results = dict(zip(keys, predictions))

    return jsonify(results)

if __name__ == "__main__":
    print("\nStarting Hate Speech Detection API...")
    app.run(
        host="0.0.0.0",
        port=4352,
        debug=True,
        threaded=True
    )