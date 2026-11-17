# Hate-Speech Detection Backend

This repository contains the backend service that accepts text-classification requests, dispatches work through RabbitMQ, runs a saved DistilBERT sequence-classification model, and stores prediction-cache and user-feedback records in SQLite.

## Components

- **Flask orchestrator (`orchestrator.py`)** — exposes the HTTP API and coordinates request/reply messages through RabbitMQ.
- **RabbitMQ worker (`app.py`)** — consumes queued jobs, runs prediction or reclassification tasks, and publishes responses.
- **Model inference (`predict.py`)** — loads the Hugging Face tokenizer and sequence-classification model and performs batched inference with PyTorch.
- **Text preprocessing (`normalize.py`)** — normalizes text and handles selected Unicode and obfuscation patterns before inference.
- **Persistence (`database.py`)** — stores cached scores and user flags in SQLite.
- **Configuration (`config.py`)** — reads paths, request limits, and RabbitMQ connection settings from environment variables.
- **Load-test utility (`TEST_ORCHESTRATOR.py`)** — sends concurrent synthetic requests to the prediction endpoint and checks response shape.

## Request flow

1. A client sends a JSON request to the Flask orchestrator.
2. The orchestrator validates the request and publishes a JSON job to the configured durable RabbitMQ queue.
3. The orchestrator creates a temporary exclusive reply queue and uses a UUID correlation ID to match the response to the request.
4. The worker consumes the job. For prediction jobs, it normalizes the texts, checks the SQLite score cache, and runs model inference for cache misses.
5. The worker publishes either a `result` or an `error` response to the supplied reply queue and acknowledges the consumed job.
6. The orchestrator returns the result to the HTTP client, or returns an error/timeout status.

## Repository contents

| File | Purpose |
|---|---|
| `app.py` | RabbitMQ worker and task handlers |
| `orchestrator.py` | Flask API and RabbitMQ request/reply coordination |
| `predict.py` | DistilBERT model loading and inference |
| `normalize.py` | Text normalization and obfuscation handling |
| `database.py` | SQLite cache and feedback persistence |
| `config.py` | Environment-based configuration |
| `TEST_ORCHESTRATOR.py` | Concurrent API load test |
| `commands.md` | Original local startup commands |
| `link.txt` | Model archive location and expected extraction path |
| `hashes.db` | SQLite database file included in the supplied archive |

## Requirements

The source imports the following third-party packages:

- `Flask`
- `pika` (RabbitMQ client)
- `torch`
- `transformers`
- `requests` (used by the load-test script)

Python's standard library is also used. Install compatible versions of these packages in your environment. The supplied archive does not include a dependency lockfile or requirements file, so exact package versions cannot be inferred from this repository alone.

## Model setup

The model archive URL recorded in `link.txt` is:

`https://jelte2357.nl/distilbert_classifier.zip`

The instructions in that file specify that the extracted directory should be:

`outputs/distilbert_classifier`

The resulting directory should contain the Hugging Face model/tokenizer files expected by `AutoTokenizer.from_pretrained` and `AutoModelForSequenceClassification.from_pretrained`. Avoid an extra nested `distilbert_classifier/distilbert_classifier` directory.

The model path can be overridden with `MODEL_DIR`.

## Start the backend

Start RabbitMQ with the management image (PowerShell command copied from `commands.md`):

```powershell
docker run -d --name rabbitmq-poc `
  -p 5672:5672 `
  -p 15672:15672 `
  rabbitmq:4-management
```

For an existing container, start it with:

```powershell
docker start rabbitmq-poc
```

The RabbitMQ management interface is normally available at `http://localhost:15672/` with the image's default development credentials unless they have been changed.

Start the worker in one terminal:

```powershell
python app.py
```

Start the Flask orchestrator in another terminal:

```powershell
python orchestrator.py
```

The orchestrator binds to `0.0.0.0:4351` when run directly. The worker does not expose an HTTP listener; it consumes RabbitMQ messages.

## Configuration

All settings below are read from environment variables and have defaults in `config.py` or `predict.py`.

| Variable | Default | Used for |
|---|---|---|
| `MODEL_DIR` | `<backend>/outputs/distilbert_classifier` | Saved model/tokenizer directory |
| `DB_PATH` | `<backend>/hashes.db` | SQLite database file |
| `MAX_BATCH_SIZE` | `128` | Defined in configuration; not referenced elsewhere in the supplied Python files |
| `MAX_REQUEST_LENGTH` | `5000` | Maximum number of key/value text entries accepted by `/api/predict` |
| `RABBITMQ_QUEUE` | `prediction_jobs` | RabbitMQ job queue name |
| `RABBITMQ_HOST` | `localhost` | RabbitMQ host |
| `RABBITMQ_PORT` | `5672` | RabbitMQ AMQP port |
| `RABBITMQ_USER` | `guest` | RabbitMQ username |
| `RABBITMQ_PASSWORD` | `guest` | RabbitMQ password |
| `MAX_LENGTH` | `256` | Maximum token length passed to the tokenizer |
| `INFERENCE_BATCH_SIZE` | `64` | Number of texts processed per model batch |
| `PORT` | `4352` | Read by `app.py` at startup but not used to bind a network listener |

`WORKER_ID` appears in the example commands in `commands.md`, but is not read by the supplied worker implementation. The `PORT` and `WORKER_ID` examples therefore do not, by themselves, configure distinct HTTP worker instances. Workers share the configured RabbitMQ queue; each process uses the configured `DB_PATH`.

## HTTP API

### `POST /api/predict`

Expects `Content-Type: application/json` and a JSON object whose keys and values are strings. Each key is preserved in the response and each value is classified.

Example request:

```json
{
  "sample_1": "Example text to classify",
  "sample_2": "Another example"
}
```

A successful response is a JSON object mapping the submitted keys to floating-point scores. The worker returns `probability[1]` from the model's softmax output; consult the model's label mapping before interpreting that value as a particular class.

Validation and failure statuses implemented by the endpoint:

| Status | Meaning in the implementation |
|---|---|
| `200` | Successful prediction, or an empty input object |
| `400` | Request is not JSON, or body is not a JSON object |
| `413` | More than `MAX_REQUEST_LENGTH` entries |
| `418` | A key or value is not a string |
| `500` | Worker response contains an error |
| `503` | RabbitMQ/OS communication error; queue reported unavailable |
| `504` | No worker response before the reply timeout |

### `POST /api/reclassify`

Expects a JSON object with a string `text` and a `flag` that is a boolean or integer `0`/`1`.

Example request:

```json
{
  "text": "Text that a user wants to flag",
  "flag": true
}
```

The worker stores a BLAKE2b hash and the supplied flag in `hash_flags`. This endpoint does **not** retrain the model or modify `hash_scores`.

Implemented statuses include `200` for success, `400` for invalid JSON/content shape, `418` for invalid field types, `500` for a worker error, `503` for queue communication errors, and `504` for a reply timeout.

## Persistence and caching

SQLite contains two tables:

- `hash_scores`: one cached score per hash. The hash is constrained to 128 lowercase hexadecimal characters and the score to the inclusive range 0.0–1.0. Inserts ignore a hash conflict rather than replacing an existing score.
- `hash_flags`: rows containing a hash and a 0/1 flag. The table does not declare the hash unique, so multiple flags for a hash can be stored.

The worker hashes normalized prediction text with BLAKE2b before looking up cached scores. Repeated texts in one prediction payload are deduplicated for inference, while output values are restored to the original input order.

## Text preprocessing

`normalize_all_apply` is the preprocessing entry point called by the prediction worker. It applies the helper transformations in the order implemented in `normalize.py`, including retweet-marker handling, optional username replacement, selected HTML entity handling, Unicode/punctuation normalization, emoji removal, and obfuscation decoding. The helper functions are documented in the source file.

## Load-test utility

Run the script with:

```powershell
python TEST_ORCHESTRATOR.py
```

The current constants configure 100 requests, 60 texts per request, 10 concurrent threads, and a 10-second HTTP timeout. It generates random alphanumeric text and checks that successful responses contain exactly the submitted keys and float scores in `[0.0, 1.0]`. This tests API throughput/response shape, not classification accuracy or model quality.

## Operational notes and implementation boundaries

- The orchestrator's reply timeout is 60 seconds (`REPLY_TIMEOUT_SECONDS`).
- The worker sets RabbitMQ prefetch to one unacknowledged message per consumer.
- The worker retries its consumer connection after an exception, waiting five seconds between attempts.
- The database lock is used by the worker around combined cache/feedback operations; the individual database methods do not acquire it internally.
- `MAX_BATCH_SIZE` is configured but unused in the supplied source; inference batching is controlled by `INFERENCE_BATCH_SIZE`.
- `app.py` reads `PORT` but starts no Flask or other HTTP server.
- The source archive contains `hashes.db` but not the trained model directory or a Python dependency lockfile.

## Scope of this documentation

This documentation describes the backend files present in the supplied archive. The model-training code, training datasets, label definitions, and model evaluation results are not included, so this README does not make claims about those parts of the project.
