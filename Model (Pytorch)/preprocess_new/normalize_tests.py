import pandas as pd
import unittest

from normalize import fix_beginning_end_quotes, _leetspeak_word

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
        self.assertEqual(_leetspeak_word("n0t l33t"), "not leet")

if __name__ == "__main__":
    unittest.main()
