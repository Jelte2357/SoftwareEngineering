import pandas as pd
import numpy as np

from normalize import normalize_text, normalize_to_ascii, normalize_all_appy

def recode_UCBerkeley_label(label: float) -> int:
    if label < 0.5:
        return 0
    else:
        return 1
    
def remove_specific_hatespeech_dataset(df: pd.DataFrame) -> pd.DataFrame:
    df = df[~((df['text'] == "content") & (df['label'] == "Label"))]
    return df

def remove_empty_text_row_cmnts(df: pd.DataFrame) -> pd.DataFrame:
    df = df[df['text'].str.strip() != '']
    return df

# XXX Process RacismDetectionDataSet
RacismDetection = pd.read_csv('./input/RacismDetectionDataSet.csv')
RacismDetection.columns = ["text", "label"]
# Select only hateful messages
RacismDetection = RacismDetection[RacismDetection['label'] == 1]
RacismDetection['text'] = RacismDetection['text'].apply(normalize_all_appy)
RacismDetection = RacismDetection.drop_duplicates(subset=['text'], keep='first')
RacismDetection = RacismDetection.dropna(subset=['text', 'label'])
RacismDetection.to_csv('./output/RacismDetectionDataSet.csv', index=False)

# XXX Process cmnts
cmnts = pd.read_csv('./input/cmnts.csv')
cmnts.columns = ["text", "label"]
cmnts["label"] = cmnts["label"].apply(lambda x: 1 if "non" in x.lower() else 0)
cmnts['text'] = cmnts['text'].apply(normalize_all_appy)
cmnts = cmnts.drop_duplicates(subset=['text'], keep='first')
cmnts = cmnts.dropna(subset=['text', 'label'])
cmnts = remove_empty_text_row_cmnts(cmnts)
cmnts.to_csv('./output/cmnts.csv', index=False)

# XXX Process HateSpeechDataset
HateSpeechDataset = pd.read_csv('./input/HateSpeechDataset.csv')
HateSpeechDataset.drop(columns=["Content_int"], inplace=True)
HateSpeechDataset.columns = ["text", "label"]
HateSpeechDataset['text'] = HateSpeechDataset['text'].apply(normalize_all_appy)
HateSpeechDataset = HateSpeechDataset.drop_duplicates(subset=['text'], keep='first')
HateSpeechDataset = HateSpeechDataset.dropna(subset=['text', 'label'])
HateSpeechDataset = remove_specific_hatespeech_dataset(HateSpeechDataset)
HateSpeechDataset.to_csv('./output/HateSpeechDataset.csv', index=False)

# Already in 3DatasetsCombined.csv
# # XXX Process labeled_data (tweets)
# labeled_data = pd.read_csv('./input/labeled_data.csv')
# labeled_data.drop(columns=["count", "hate_speech", "offensive_language", "neither"], inplace=True)
# labeled_data.drop(labeled_data.columns[0], axis=1, inplace=True)
# labeled_data.columns = ["label", "text"]
# labeled_data = labeled_data.reindex(columns=["text", "label"])
# labeled_data['text'] = labeled_data['text'].apply(normalize_all_appy)
# labeled_data = labeled_data.drop_duplicates(subset=['text'], keep='first')
# labeled_data = labeled_data.dropna(subset=['text', 'label'])
# labeled_data.to_csv('./output/labeled_data.csv', index=False)

# XXX Process 3DatasetsCombined (possibly bad)
DatasetsCombined = pd.read_csv('./input/3DatasetsCombined.csv')
DatasetsCombined.columns = ["text", "label"]
DatasetsCombined['text'] = DatasetsCombined['text'].apply(normalize_all_appy)
DatasetsCombined = DatasetsCombined.drop_duplicates(subset=['text'], keep='first')
DatasetsCombined = DatasetsCombined.dropna(subset=['text', 'label'])
DatasetsCombined.to_csv('./output/3DatasetsCombined.csv', index=False)

# XXX Process UCBerkeley
UCBerkeley = pd.read_csv('./input/UCBerkeley.csv')
UCBerkeley = UCBerkeley[["hate_speech_score", "text"]]
UCBerkeley.columns = ["label", "text"]
UCBerkeley = UCBerkeley.reindex(columns=["text", "label"])
UCBerkeley['text'] = UCBerkeley['text'].apply(normalize_all_appy)
UCBerkeley['label'] = UCBerkeley['label'].apply(recode_UCBerkeley_label)
UCBerkeley = UCBerkeley.drop_duplicates(subset=['text'], keep='first')
UCBerkeley = UCBerkeley.dropna(subset=['text', 'label'])
UCBerkeley.to_csv('./output/UCBerkeley.csv', index=False)