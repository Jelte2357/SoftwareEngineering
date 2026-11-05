import pandas as pd
import unittest

from process import remove_empty_text_row_cmnts, recode_UCBerkeley_label


#--- Functions ---

# def recode_UCBerkeley_label(label: float) -> int:
#     if label < 0.5:
#         return 0
#     else:
#         return 1

# def remove_specific_hatespeech_dataset(df: pd.DataFrame) -> pd.DataFrame:
#     df = df[~((df['text'] == "content") & (df['label'] == "Label"))]
#     return df

# def remove_empty_text_row_cmnts(df: pd.DataFrame) -> pd.DataFrame:
#     df = df[df['text'].str.strip() != '']
#     return df

#--- Tests ---

class ProcessingTests(unittest.TestCase):
    def test_recode_threshold(self): # Checks if the threshold works, especially at 0.5
        self.assertEqual(recode_UCBerkeley_label(0.3), 0)
        self.assertEqual(recode_UCBerkeley_label(0.5), 1)
        self.assertEqual(recode_UCBerkeley_label(0.8), 1)

    def test_remove_empties(self): # Does remove_empty_text_row_cmnts() do its job?
        df = pd.DataFrame({
            "text": ["Greetings", "", "man", "   "],
            "label": [1, 0, 1, 0]
        })

        result = remove_empty_text_row_cmnts(df)
        self.assertEqual(list(result["text"]), ["Greetings", "man"])

    def test_remove_empties_keeps_og_labels(self): # Tests if the labels stay the same after empty strings are removed
        df = pd.DataFrame({
            "text": ["Hello", "", "World"],
            "label": [1, 0, 0]
        })

        result = remove_empty_text_row_cmnts(df)
        self.assertEqual(list(result["label"]), [1, 0])

    def test_remove_empties_works_with_empty_DF(self): # Tests if an empty dataframe works
        df = pd.DataFrame({
                    "text": [], 
                    "label": []
                })
        result = remove_empty_text_row_cmnts(df)
        self.assertTrue(result.empty)
        self.assertEqual(list(result.columns), ["text", "label"])

    def test_remove_empties_works_with_missing_values(self): # Tests if a dataframe with missing values works
        df = pd.DataFrame({
            "text": ["Hello", None, "World"],
            "label": [1, 0, 0] 
        })
        result = remove_empty_text_row_cmnts(df)
        self.assertEqual(list(result["text"]), ["Hello", "World"])

if __name__ == "__main__":
    unittest.main()
