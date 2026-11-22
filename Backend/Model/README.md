# DistilBERT CSV classifier (PyTorch Lightning)

Train a binary classifier from a CSV with columns named `text` and `label` (labels must be `0` or `1`).
Put `data.csv` in this folder, or edit `CSV_PATH` in `train_distilbert.py` to point to your CSV.

## Train
```powershell
python train_distilbert.py
```

The script tokenizes in batches, stores the tokenized data on disk under `cache/`, and reuses the cache on the next run. Cache location changes when the CSV file size or modification time changes. For a quick initial experiment, set `MAX_TRAIN_EXAMPLES = 5_000` in the config; set it to `None` for full training on all training rows.
Model checkpoints are written to `outputs/checkpoints/`; the best model and tokenizer are exported to `outputs/distilbert_classifier/`.

## Predict
```powershell
python predict.py --text "I liked this" --text "You are an idiot"
```

The output contains a the predicted classes (`0` and `1` [no hatespeech / hatespeech]) and the probability assigned to that predicted class.

## Memory and speed controls
- `MAX_LENGTH = 256` strictly truncates text inputs to at most 256 tokens.
- The complete dataset is not loaded onto the GPU. Only one batch is transferred for each step.
- `NUM_WORKERS = 0` to avoid windows multiprocessing issues.
- Training defaults to three epochs, with early stopping and a best-validation-macro-F1 checkpoint. A 5% validation split is held out from training.

The model predicts labels from examples; it must still be trained on your CSV before `predict.py` can be used.
In order to correctly run train_distilbert.py, unzip the dataset (data.7z) to a csv. Then run train_distilbert.py.
