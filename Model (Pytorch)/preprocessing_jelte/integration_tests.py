import pandas as pd
import pytest

from normalize import normalize_text

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

validated = [
    "you are so worthlessanobody likes you", 
    "@annafootball yoou are s00 uugly lol",
    "have a great day everyone",
    "just chatting about c++ and node.js url",
    "i have 3 cats and 1 dog url",
    "aaaa",
    "hello word",
    "hello world",
    "ello word",
    "word email split by zero-width space",
    "word with nbsp spaces",
    "this is glitched",
    "hello",
    "café naïve",
    "copy and paste emoji no apps required",
    "aayyaa",
    "death':",
    "hello this is subscript text",
    "hello this is superscript text",
    "hello this is superscript text"
    ]

def test_normalize(examples):
    results = []
    for ex in examples:
        results.append(normalize_text(ex))
    for i, (actual, expected) in enumerate(zip(results, validated)):
        if actual != expected:
                print(f"Mistake at index {i}, expected: {expected}, result: {actual}")
    assert normalize_text(examples) == validated

def main():
    test_normalize(examples)


if __name__ == "__main__":
    main()