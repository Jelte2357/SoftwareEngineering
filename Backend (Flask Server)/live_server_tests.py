import pandas as pd
import unittest
import requests
import random
from string import printable
#--- Tests ---

def generate_random_string(length: int) -> str:
    return ''.join(random.choice(printable) for _ in range(length))

class LiveTests(unittest.TestCase):
    def test_predict(self): # Tests if the function removes quotes at the beginning and end of the text
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/predict", json={"uuid4": "hello world"}).status_code,
            200
        )
        self.assertTrue(
            0 <= requests.post("http://127.0.0.1:4352/api/predict", json={"uuid4": "hello world"}).json()["uuid4"] <= 1
        )
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/predict", json=[]).status_code,
            400
        )
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/predict", json={"uuid4": 123}).status_code,
            418
        )
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/predict").status_code,
            400
        )
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/predict", json={r: r for r in [generate_random_string(10) for _ in range(5001)]}).status_code,
            413
        )
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/predict", json={r: r for r in [generate_random_string(10000)]}).status_code,
            200
        )
        
    def test_reclassify(self):
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/reclassify", json={"text": "Hi guys!", "flag": 0}).status_code,
            200
        )
        
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/reclassify", json={"text": "Hi guys!", "flag": 2}).status_code,
            418
        )
        
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/reclassify", json={"text": 123, "flag": 0}).status_code,
            418
        )

        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/reclassify", json=[]).status_code,
            400
        )
        
        self.assertEqual(
            requests.post("http://127.0.0.1:4352/api/reclassify").status_code,
            400
        )
        
if __name__ == "__main__":
    unittest.main()
