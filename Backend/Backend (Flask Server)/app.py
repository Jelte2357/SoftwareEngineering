import hashlib
import normalize

from config import *
from database import Database
from flask import Flask, jsonify, request
from predict import HateSpeechPredictor
from typing import cast

app = Flask(__name__)

app.config["MAX_REQUEST_LENGTH"] = MAX_REQUEST_LENGTH
app.config["MAX_BATCH_SIZE"] = MAX_BATCH_SIZE

classifier = HateSpeechPredictor(
    model_dir=MODEL_DIR,
)

db = Database(db_path=DB_PATH)

def predict_texts(texts: tuple[str]) -> list[float]:
    unique_texts = dict.fromkeys(texts)  # Remove duplicates while preserving order
    text_to_hash = {text: hashlib.blake2b(text.encode("utf-8")).hexdigest() for text in unique_texts}
    hash_to_text = {hash: text for text, hash in text_to_hash.items()}

    with db.lock:
        known, missing = db.get_scores(list(hash_to_text.keys()))
        known_predictions = {hash_to_text[hash]: score for hash, score in known.items()}
        missing_predictions = {}
        if missing:
            missing_texts = [hash_to_text[hash] for hash in missing]
            missing_predictions = dict(zip(missing_texts, classifier.predict(missing_texts)))
            db.insert_scores({text_to_hash[text]: score for text, score in missing_predictions.items()})
    
    all_predictions = {**known_predictions, **missing_predictions}
    return [all_predictions[text] for text in texts]

@app.route("/api/predict", methods=["POST"]) 
def api_predict():

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
    texts = cast(tuple[str], tuple(map(normalize.normalize_all_apply, texts)))
    predictions = predict_texts(texts)
    results = dict(zip(keys, predictions))
    
    return jsonify(results)

@app.route("/api/reclassify", methods=["POST"]) 
def api_reclassify():

    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json."
        }), 400

    payload = request.get_json(silent=True)

    if not isinstance(payload, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    text = payload.get("text") 
    flag = payload.get("flag") 

    if not isinstance(text, str) or not (isinstance(flag, bool) or (isinstance(flag, int) and flag in (0, 1))):
        return jsonify({
            "error": "Request body must contain 'text' (string) and 'flag' (boolean)."
        }), 418 
        
    if len(payload) > MAX_REQUEST_LENGTH:
        return jsonify({
            "error": f"Request body must contain at most {MAX_REQUEST_LENGTH} texts."
        }), 413

    text_hash = hashlib.blake2b(text.encode("utf-8")).hexdigest()

    with db.lock:
        db.insert_flag(text_hash, bool(flag)) 

    return jsonify({"hash": text_hash, "flag": flag, "message": "saved"}), 200

if __name__ == "__main__":
    print("\nStarting Hate Speech Detection API...")
    app.run(
        host="0.0.0.0",
        port=4352,
        debug=True,
        threaded=True
    )