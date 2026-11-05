import pandas as pd
import unittest
import predict
import database
#--- Tests ---

global model, db
model = predict.HateSpeechPredictor()
db = database.Database()

class NormalizeTests(unittest.TestCase):
    def test_prediction(self): # Tests if the function removes quotes at the beginning and end of the text
        self.assertTrue(0 <= model.predict(["hello world"])[0] <= 1)
    
    def test_get_scores(self): # Tests if the function correctly converts leetspeak to normal text
        found, missing = db.get_scores(["notexistinghash", "0007cc123d45aac017697457b0f552e528b32993ab136b5bc19d7bd088d333e8e3446becf4120c1290b7fcf9688be1f7c67810935ad512d0e74f97f074f3c419"])
        self.assertIsInstance(found, dict)
        self.assertIsInstance(missing, list)
        self.assertEqual(len(found) + len(missing), 2)
        self.assertIn("notexistinghash", missing)
        self.assertIn("0007cc123d45aac017697457b0f552e528b32993ab136b5bc19d7bd088d333e8e3446becf4120c1290b7fcf9688be1f7c67810935ad512d0e74f97f074f3c419", found)
        
    def test_get_flags(self): # Tests if the function correctly converts leetspeak to normal text
        flags = db.get_all_flags()
        self.assertIsInstance(flags, list)
        for hash_value, flag in flags:
            self.assertIsInstance(hash_value, str)
            self.assertIsInstance(flag, bool)

if __name__ == "__main__":
    unittest.main()
