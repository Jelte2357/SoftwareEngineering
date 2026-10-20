import re
import unicodedata

URL_PATTERN = re.compile(r"(https?://\S+|www\.\S+\.\S+)", re.IGNORECASE) # Website links
EMAIL_PATTERN = re.compile(r"\b[\w.+-]+@[\w-]+\.[a-zA-Z]{2,}\b") # Email addresses

def _redact_structural_tokens(text: str) -> str:
    text = URL_PATTERN.sub(" url ", text)
    text = EMAIL_PATTERN.sub(" email ", text)
    return text

PUNCTUATION_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u2032": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"', "\u2033": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-",
}

def _fix_punctuation(text: str) -> str:
    return "".join(PUNCTUATION_MAP.get(c, c) for c in text)

LEET_MAP = {
    "@": "a", "4": "a", "3": "e", "1": "i", "!": "i", "0": "o", "$": "s", "5": "s", "6": "g", "7": "t", "+": "t", "9": "g", "8": "b",
}

def _leetspeak_word(word: str) -> str:
    # Requires at least 2 real letters, at least one leet character, and the leet characters not outnumbering the real letters.
    letters = sum(c.isalpha() for c in word)
    leets = sum(c in LEET_MAP for c in word)
    if letters < 2 or leets == 0 or leets > letters:
        return word

    # Keep leading/trailing @ and ! intact unless the word contains another
    # kind of leetspeak character.  This avoids corrupting mentions and
    # exclamations while still decoding them when they are clearly obfuscated.
    has_other_leet = any(c in LEET_MAP and c not in "@!" for c in word)
    last_index = len(word) - 1
    return "".join(
        c if c in "@!" and index in (0, last_index) and not has_other_leet
        else LEET_MAP.get(c, c)
        for index, c in enumerate(word)
    )

LOOKALIKE_MAP = {
    # Cyrillic homoglyphs
    "а": "a", "А": "A",
    "е": "e", "Е": "E",
    "о": "o", "О": "O",
    "р": "p", "Р": "P",
    "с": "c", "С": "C",
    "у": "y", "У": "Y",
    "х": "x", "Х": "X",
    "і": "i", "І": "I",
    "ѕ": "s", "Ѕ": "S",
    "м": "m", "М": "M",
    "н": "H", "Н": "H",
    "в": "B", "В": "B",
    "к": "K", "К": "K",
    "т": "T", "Т": "T",

    # Greek
    "α": "a", "Α": "A",
    "ο": "o", "Ο": "O",
    "ρ": "p", "Ρ": "P",
    "υ": "u", "Υ": "Y",
    "ν": "v", "Ν": "N",
    "κ": "k", "Κ": "K",
    "χ": "x", "Χ": "X",
    "τ": "t", "Τ": "T",
    "ι": "i", "Ι": "I",
}

def _fix_lookalikes(text: str) -> str:
    return "".join(LOOKALIKE_MAP.get(c, c) for c in text)

NORMAL_TO_FLIP = {
    "a": "ɐ", "b": "q", "c": "ɔ", "d": "p", "e": "ǝ", "f": "ɟ", "g": "ƃ",
    "h": "ɥ", "i": "ᴉ", "j": "ɾ", "k": "ʞ", "l": "l", "m": "ɯ", "n": "u",
    "o": "o", "p": "d", "q": "b", "r": "ɹ", "s": "s", "t": "ʇ", "u": "n",
    "v": "ʌ", "w": "ʍ", "x": "x", "y": "ʎ", "z": "z",
}
FLIP_TO_NORMAL = {flip: normal for normal, flip in NORMAL_TO_FLIP.items()}

SUPERSCRIPT_TO_LETTER = {
    "ᵃ": "a", "ᵇ": "b", "ᶜ": "c", "ᵈ": "d", "ᵉ": "e", "ᶠ": "f", "ᵍ": "g",
    "ʰ": "h", "ⁱ": "i", "ʲ": "j", "ᵏ": "k", "ˡ": "l", "ᵐ": "m", "ⁿ": "n",
    "ᵒ": "o", "ᵖ": "p", "ʳ": "r", "ˢ": "s", "ᵗ": "t", "ᵘ": "u", "ᵛ": "v",
    "ʷ": "w", "ˣ": "x", "ʸ": "y", "ᶻ": "z",
    "º": "o",
}

SUBSCRIPT_TO_LETTER = {
    "ₐ": "a", "ₑ": "e", "ₕ": "h", "ᵢ": "i", "ⱼ": "j", "ₖ": "k", "ₗ": "l", 
    "ₘ": "m", "ₙ": "n", "ₒ": "o", "ₚ": "p", "ᵣ": "r", "ₛ": "s", "ₜ": "t",
    "ᵤ": "u", "ᵥ": "v", "ₓ": "x", "₊": "+", "₋": "-", "₌": "=", "₍": "(", "₎": ")",
}

_DISTINCTIVE_FLIP_CHARS = {
    flip for normal, flip in NORMAL_TO_FLIP.items() if flip != normal and ord(flip) > 127
}
_DISTINCTIVE_FLIP_CHARS |= set(SUPERSCRIPT_TO_LETTER.keys())
_DISTINCTIVE_FLIP_CHARS |= set(SUBSCRIPT_TO_LETTER.keys())

def _decode_flip_char(c: str) -> str:
    base = SUPERSCRIPT_TO_LETTER.get(c, SUBSCRIPT_TO_LETTER.get(c, c))
    return FLIP_TO_NORMAL.get(base, base)

def _looks_upside_down(text: str, threshold: float = 0.3) -> bool:
    letters = [c for c in text if c.isalpha()]
    if len(letters) < 4:
        return False
    flip_count = sum(1 for c in letters if c in _DISTINCTIVE_FLIP_CHARS)
    return (flip_count / len(letters)) >= threshold

def _fix_upside_down(text: str) -> str:
    decoded = [_decode_flip_char(c) for c in text]
    decoded.reverse()
    return "".join(decoded)

def _strip_combining_marks(text: str) -> str:
    return "".join(c for c in text if unicodedata.category(c) not in {"Mn", "Me"})

EMOJI_PATTERN = re.compile( # This is just regex for all emojis
    "["
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002600-\U000026FF"
    "\U00002700-\U000027BF"
    "]+",
    flags=re.UNICODE,
)
VARIATION_SELECTORS = re.compile(r"[\uFE00-\uFE0F]")

def _strip_emoji(text: str) -> str:
    text = EMOJI_PATTERN.sub("", text)
    text = VARIATION_SELECTORS.sub("", text)
    return text

SEPARATOR_CHARS = r"[\^;_~|>=]"
SEPARATOR_BETWEEN_WORDS = re.compile(rf"(?<=\w){SEPARATOR_CHARS}(?=\w)")
REPEAT_CHAR = re.compile(r"(.)\1{2,}")
WIDE_SPACE = re.compile(r"[\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]")
ZERO_WIDTH = re.compile(r"[\u200B\u200C\u200D\uFEFF\u2060]")

def _only_printable(text: str) -> str:
    return "".join(c for c in text if c.isprintable() or c in "\n\r\t" or c.isspace())

def normalize_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)

    text = text.replace(" #", " ")
    
    text = _redact_structural_tokens(text)
    text = _fix_punctuation(text)
    text = unicodedata.normalize("NFKC", text)
    text = _strip_combining_marks(text)
    text = _strip_emoji(text)
    text = REPEAT_CHAR.sub(r"\1\1", text)
    text = _fix_lookalikes(text)

    if _looks_upside_down(text):
        text = _fix_upside_down(text)

    text = WIDE_SPACE.sub(" ", text)
    text = ZERO_WIDTH.sub("", text)
    text = SEPARATOR_BETWEEN_WORDS.sub(" ", text)
    text = " ".join(_leetspeak_word(w) for w in text.split())
    text = re.sub(r"\s+", " ", text).strip().lower()

    text = _only_printable(text)

    return text

def normalize_to_ascii(text: str) -> str:
    text = normalize_text(text)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    return text

def drop_RT(text: str) -> str:
    return text.replace(" RT ", "")

def replace_at_usernames(text: str) -> str:
    return re.sub(r"@\w+", " user ", text)

def remove_ampersand_with_hashtag_numbers(text: str) -> str:
    return re.sub(r"&#\d+;", "", text)

def remove_andamp(text: str) -> str:
    return text.replace("&amp;", " and ")

def fix_beginning_end_quotes(text: str) -> str:
    # Removes quotation marks (" or ') at the beginning and end of entire text; only if they are at both ends and are the same type of quote.
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'} and text.count(text[0]) == 2:
        return text[1:-1]
    return text.strip()
    

def normalize_all_appy(text: str, keep_usernames: bool = True) -> str:
    text = drop_RT(text)
    if not keep_usernames:
        text = replace_at_usernames(text)
    text = remove_ampersand_with_hashtag_numbers(text)
    text = remove_andamp(text)
    text = normalize_text(text)
    text = fix_beginning_end_quotes(text)
    return text

if __name__ == "__main__":
    examples = [
        "you^are;so;w0rthl3ss@nobody^likes;you",
        "@annaFootball y0000u are s000 uuuuugly lol",
        "h4ve a gr34t d4y everyone",
        "just chatting about c++ and node.js https://example.com",
        "i have 3 cats and 1 dog www.example.com/abc",
        "aаааa",
        "pɹoʍ ollǝɥ",
        "ｈｅｌｌｏ ｗｏｒｌｄ",
        "ᵖɹᵒʍ ºllǝ",
        "w\u200bord ja.k@gmail.com split by zero-width space",
        "word\u00a0with\u00a0nbsp\u00a0spaces",
        "t̶h̶i̶s̶ ̶i̶s̶ ̶g̶l̶i̶t̶c̶h̶e̶d̶",
        "ℎ𝑒𝑙𝑙𝑜",
        "café naïve",
        "✂️ Copy and 📋 Paste Emoji 👍 No apps required",
        "aaaуууaaa",
        " death’: ",
        "ₕₑₗₗₒ ₜₕᵢₛ ᵢₛ ₛᵤbₛcᵣᵢₚₜ ₜₑₓₜ",
        "ʰᵉˡˡᵒ ᵗʰⁱˢ ⁱˢ ˢᵘᵖᵉʳˢᶜʳⁱᵖᵗ ᵗᵉˣᵗ",
        "ₕᵉₗˡₒ ₜₕᶦₛ ⁱₛ ₛᵘᵖₑʳˢᶜʳⁱₚₜ ₜₑₓₜ",
    ]
    for ex in examples:
        print(f"{ex!r:55s} -> {normalize_text(ex)!r}")