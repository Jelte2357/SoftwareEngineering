# DistilBERT CSV classifier (PyTorch Lightning)

Train a binary classifier from a CSV with columns named `text` and `label` (labels must be `0` or `1`).

## Windows setup

Use Python 3.10 or 3.11 in a virtual environment. Install a PyTorch build matching your CUDA setup from <https://pytorch.org/get-started/locally/> first if GPU training is desired, then run:

```powershell
python -m pip install -r requirements.txt
```

Put `data.csv` in this folder, or edit `CSV_PATH` in `train_distilbert.py` to point to your CSV.

## Train

```powershell
python train_distilbert.py
```

The script tokenizes in batches, stores the tokenized data on disk under `cache/`, and reuses the cache on the next run. Cache location changes when the CSV file size or modification time changes. Remove the relevant `cache` folder if you want to force reprocessing. For a quick initial experiment, set `MAX_TRAIN_EXAMPLES = 50_000` in the config; set it to `None` for full training on all training rows.

Model checkpoints are written to `outputs/checkpoints/`; the best model and tokenizer are exported to `outputs/distilbert_classifier/`.

## Predict

```powershell
python predict.py --text "I liked this" --text "I hated this"
```

The output contains a predicted class (`0` or `1`) and the probability assigned to that predicted class. This confidence is not guaranteed to be calibrated.

## Memory and speed controls

- `MAX_LENGTH = 256` strictly truncates text inputs to at most 256 tokens.
- The complete dataset is not loaded onto the GPU. Only one batch is transferred for each step.
- `BATCH_SIZE = 16` and `GRADIENT_ACCUMULATION = 2` give an effective batch size of 32. If you get CUDA out-of-memory errors, reduce `BATCH_SIZE` to `8` or `4`.
- `NUM_WORKERS = 0` avoids Windows multiprocessing issues.
- Dynamic padding pads each batch to its longest sequence (up to 256) instead of padding every example to 256 in advance.
- Mixed precision is enabled on CUDA to lower memory use; CPU runs use full precision.
- Training defaults to three epochs, with early stopping and a best-validation-macro-F1 checkpoint. A 5% validation split is held out from training.

The model predicts labels from examples; it must still be trained on your CSV before `predict.py` can be used.
