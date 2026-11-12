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


def test_english_medical_text_is_not_flagged():
    from pathlib import Path

    from omaker.domain.text import looks_non_english
    for name in ("sample_text.txt", "sample_text_2.txt"):
        assert not looks_non_english((Path(__file__).parent / name).read_text(encoding="utf-8"))


def test_portuguese_and_spanish_texts_are_flagged():
    from omaker.domain.text import looks_non_english
    pt = ("A metformina é o tratamento de primeira linha para o diabetes tipo 2. O uso prolongado da "
          "metformina pode causar deficiência de vitamina B12 em pacientes que não fazem acompanhamento.")
    es = ("La metformina es el tratamiento de primera línea para la diabetes tipo 2 y su uso prolongado "
          "puede causar deficiencia de vitamina B12 en los pacientes con enfermedad renal.")
    assert looks_non_english(pt)
    assert looks_non_english(es)


def test_short_text_is_never_flagged():
    from omaker.domain.text import looks_non_english
    assert not looks_non_english("Aspirina trata dor.")
