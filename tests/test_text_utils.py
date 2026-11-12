from omaker.domain.text import split_sentences


def sentences(text):
    return [text[s:e] for s, e in split_sentences(text)]


def test_split_keeps_title_abbreviations():
    assert sentences("Dr. Smith gave aspirin. The patient improved.") == [
        "Dr. Smith gave aspirin.",
        "The patient improved.",
    ]


def test_split_keeps_latin_and_figure_abbreviations():
    text = "Analgesics, e.g. Aspirin, reduce fever. See Fig. 2 for details. Aspirin vs. Ibuprofen was tested."
    assert sentences(text) == [
        "Analgesics, e.g. Aspirin, reduce fever.",
        "See Fig. 2 for details.",
        "Aspirin vs. Ibuprofen was tested.",
    ]


def test_split_still_splits_real_boundaries():
    text = "Aspirin prevents stroke. Chemotherapy causes nausea! Is 5 mg safe? Yes. Hepatitis B. Patients recovered."
    assert sentences(text) == [
        "Aspirin prevents stroke.",
        "Chemotherapy causes nausea!",
        "Is 5 mg safe?",
        "Yes.",
        "Hepatitis B.",
        "Patients recovered.",
    ]
