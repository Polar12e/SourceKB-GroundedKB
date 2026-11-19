from domains.finance.lexicon import (
    CONCEPT_GROUPS,
    EXPANSION_WEIGHT,
    concepts_for,
    expand_terms,
)


def test_colloquial_wording_maps_to_line_items() -> None:
    assert "存货" in concepts_for("公司仓库里压了多少货")
    assert "研发投入" in concepts_for("公司一年在技术上要投多少钱")
    assert "质押" in concepts_for("大股东的股票有没有被抵押出去")


def test_matching_is_on_bigrams_not_substrings() -> None:
    assert "技术投入" not in "公司一年在技术上要投多少钱"
    assert "研发投入" in concepts_for("公司一年在技术上要投多少钱")


def test_terms_already_present_are_not_repeated() -> None:
    assert "存货" not in concepts_for("存货有多少")


def test_rewrite_weight_is_below_full_weight() -> None:
    assert 0 < EXPANSION_WEIGHT < 1
    assert all(weight == EXPANSION_WEIGHT for _, weight in expand_terms("仓库里压了多少货"))


def test_concept_members_are_not_single_characters() -> None:
    for group in CONCEPT_GROUPS:
        for member in group:
            assert len(member) > 1
