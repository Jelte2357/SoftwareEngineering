import pandas as pd
import unittest
import predict
import database
#--- Tests ---

class ServerTests(unittest.TestCase):
    def test_prediction(self): # Tests if the function removes quotes at the beginning and end of the text
        model = predict.HateSpeechPredictor()
        self.assertTrue(0 <= model.predict(["hello world"])[0] <= 1)
    
    def test_get_scores(self):
        db = database.Database()
        found, missing = db.get_scores(["notexistinghash", "0007cc123d45aac017697457b0f552e528b32993ab136b5bc19d7bd088d333e8e3446becf4120c1290b7fcf9688be1f7c67810935ad512d0e74f97f074f3c419"])
        self.assertIsInstance(found, dict)
        self.assertIsInstance(missing, list)
        self.assertEqual(len(found) + len(missing), 2)
        self.assertIn("notexistinghash", missing)
        self.assertIn("0007cc123d45aac017697457b0f552e528b32993ab136b5bc19d7bd088d333e8e3446becf4120c1290b7fcf9688be1f7c67810935ad512d0e74f97f074f3c419", found)
        
    def test_get_flags(self): 
        db = database.Database()
        flags = db.get_all_flags()
        self.assertIsInstance(flags, list)
        for hash_value, flag in flags:
            self.assertIsInstance(hash_value, str)
            self.assertIsInstance(flag, bool)

if __name__ == "__main__":
    unittest.main()
