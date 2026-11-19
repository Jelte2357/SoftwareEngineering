import pandas as pd
import unittest

from normalize import fix_beginning_end_quotes, _leetspeak_word, _strip_emoji

#--- Tests ---

class NormalizeTests(unittest.TestCase):
    def test_fix_beginning_end_quotes(self): # Tests if the function removes quotes at the beginning and end of the text
        self.assertEqual(fix_beginning_end_quotes('"Hello World"'), "Hello World")
        self.assertEqual(fix_beginning_end_quotes("'Hello World'"), "Hello World")
        self.assertEqual(fix_beginning_end_quotes('"Hello World\''), '"Hello World\'')
        self.assertEqual(fix_beginning_end_quotes("'Hello World\""), "'Hello World\"")
        self.assertEqual(fix_beginning_end_quotes("No quotes here"), "No quotes here")
    
    def test_leetspeak_word(self): # Tests if the function correctly converts leetspeak to normal text
        self.assertEqual(_leetspeak_word("h3ll0"), "hello")
        self.assertEqual(_leetspeak_word("w0rld"), "world")
        self.assertEqual(_leetspeak_word("leet"), "leet")
        self.assertEqual(_leetspeak_word("1337"), "1337") # Not "clearly" leetspeak

    def test_strip_emoji(self):
        self.assertEqual(_strip_emoji("Hello 😊"), "Hello ")
        self.assertEqual(_strip_emoji("No emoji here!"), "No emoji here!")
        self.assertEqual(_strip_emoji("Multiple emojis 😂😂"), "Multiple emojis ")
        self.assertEqual(_strip_emoji("Glasses 😎"), "Glasses ")
        self.assertEqual(_strip_emoji("🐍 Hello"), " Hello")
        self.assertEqual(_strip_emoji("Combination emoji 👨‍👨‍👦"), "Combination emoji ‍‍") # 2 zero width spaces, those are dropped in another fucntion

if __name__ == "__main__":
    unittest.main()
