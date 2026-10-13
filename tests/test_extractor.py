import pytest

from law_links import ROOT
from scripts.eval import evaluate, load_cases, to_key

GOLD = ROOT / "tests" / "gold.json"
CASES = load_cases(GOLD)
# Known disagreements with the gold set, kept visible instead of tuned away.
KNOWN = {
    "neg_sentence_boundary": "'ст. 5. НК РФ': a dot after the article number is read as part of the chain",
}


@pytest.mark.parametrize(
    "case",
    [pytest.param(c, marks=pytest.mark.xfail(reason=KNOWN[c["id"]], strict=True)) if c["id"] in KNOWN else c for c in CASES],
    ids=[c["id"] for c in CASES],
)
def test_gold_case(extractor, case):
    predicted = [to_key(link.model_dump()) for link in extractor.extract(case["text"])]
    expected = [to_key(link) for link in case["links"]]
    assert sorted(predicted, key=str) == sorted(expected, key=str)


def test_order_follows_text(extractor):
    links = extractor.extract("ст. 1 УК РФ и ст. 2 НК РФ")
    assert [(l.law_id, l.article) for l in links] == [(13, "1"), (15, "2")]


def test_enumeration_shares_law(extractor):
    links = extractor.extract("с учетом ч. 6 ст. 15, ст.ст. 64 и 73 УК РФ")
    assert [(l.law_id, l.article, l.point_article) for l in links] == [
        (13, "15", "6"), (13, "64", None), (13, "73", None),
    ]


def test_anaphora(extractor):
    links = extractor.extract("по ч. 1 ст. 19.5 КоАП РФ. Срок по ч. 24 ст. 19.5 названного Кодекса истек.")
    assert [(l.law_id, l.point_article) for l in links] == [(17, "1"), (17, "24")]


def test_law_named_before_chain(extractor):
    text = (
        "Согласно Уголовному кодексу Российской Федерации, ответственность за соответствующее деяние "
        "предусмотрена статьёй 105. При этом статья 106 того же Кодекса устанавливает специальный состав."
    )
    assert [(l.law_id, l.article) for l in extractor.extract(text)] == [(13, "105"), (13, "106")]
    links = extractor.extract("По УК РФ ст. 105 и ст. 106 наказываются")
    assert [(l.law_id, l.article) for l in links] == [(13, "105"), (13, "106")]
    # An enumeration still takes the law after its last chain.
    links = extractor.extract("По УК РФ ст. 105, ст. 106 и ч. 1 ст. 2 НК РФ")
    assert [(l.law_id, l.article) for l in links] == [(15, "105"), (15, "106"), (15, "2")]


def test_law_before_chain_needs_document_word(extractor):
    # "связи" and "аренды" are short titles of laws, not law names here.
    assert extractor.extract("в связи со смертью кормильца (статья 1089)") == []
    assert extractor.extract("Гражданского кодекса РФ согласно пункту 4 статьи 25 Федерального закона о регистрации") == []


# Misses found by the survey (docs/SURVEY.md).
@pytest.mark.parametrize(
    "text, expected",
    [
        ("учитывая положения статьи 150, 272 КАС РФ, суд рассмотрел дело", [(18, "150"), (18, "272")]),
        ("руководствуясь ст.29.9, ст.29.10 КРФоАП, мировой судья", [(17, "29.9"), (17, "29.10")]),
        ("предусмотренного ч.1 ст.5.42 Кодекса РФ об АП, в отношении", [(17, "5.42")]),
        ("Частью 6 статьи 10 ФЗ № 149 запрещено распространение информации", [(331, "10")]),
        ("определяется в соответствии со статьей 12 Федерального закона от 25 апреля 2002 г. № 40-ФЗ.", [(397, "12")]),
        (
            "в нарушение установленного ч. 4 ст. 20 Федерального закона от 27 июля 2006 года № 152-ФЗ "
            "«О персональных данных» срока",
            [(330, "20")],
        ),
    ],
)
def test_survey_misses(extractor, text, expected):
    assert [(l.law_id, l.article) for l in extractor.extract(text)] == expected


def test_anaphora_to_law_named_without_chain(extractor):
    text = (
        "Отношения регулируются нормами Закона РФ «О защите прав потребителей».\n"
        "Согласно ч. 1 ст. 16 вышеназванного Закона условия договора недействительны."
    )
    assert [(l.law_id, l.article) for l in extractor.extract(text)] == [(984, "16")]
    # "Закона" does not point to a code.
    text = "Отношения регулируются Гражданским кодексом РФ. Согласно ст. 16 вышеназванного Закона условия недействительны."
    assert extractor.extract(text) == []


def test_shared_law_number_by_context(extractor):
    text = "протокол опроса, проведенного адвокатом в соответствии с подп. 2 п. 3 ст. 6 Закона N 63-ФЗ"
    assert [l.law_id for l in extractor.extract(text)] == [396]


def test_gold_f1(extractor):
    assert evaluate(extractor, CASES)["f1"] >= 0.98
