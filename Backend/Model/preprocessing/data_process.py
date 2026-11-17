import pandas as pd
import regex
from tqdm import tqdm
from normalize import normalize_all_apply

data = pd.read_csv("data_in.csv")

text_data, text = data.Content, list(map(str, data.Content.to_list()))
label_data, label = data.Label, list(map(int, data.Label.to_list()))

normalized_text = [normalize_all_apply(t) for t in tqdm(text, total=len(text), desc="Normalizing text")]



total = 0
mapping = {}
conflicting_pairs = set()

for A, B in zip(normalized_text, label):
    if A not in mapping:
        mapping[A] = B
    else:
        if mapping[A] != B:
            conflicting_pairs.add(A)
            total += 1
     
good_pairs = {A: B for A, B in zip(normalized_text, label) if A not in conflicting_pairs}       

print(f"percentage: {total / len(normalized_text) * 100:.2f}")

cleaned_text, label = zip(*good_pairs.items())

new_data = pd.DataFrame({"text": cleaned_text, "label": label})
new_data.to_csv('data.csv', index=False)