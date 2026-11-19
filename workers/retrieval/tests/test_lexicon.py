from pathlib import Path

from core.retrieval.terms import load_term_table, terms_for

ROOT = Path(__file__).resolve().parents[3]
TABLE = load_term_table(ROOT / "domains" / "finance" / "terms.json")


def test_colloquial_wording_maps_to_line_items() -> None:
    assert "存货" in terms_for("公司仓库里压了多少货", TABLE)
    assert "研发投入" in terms_for("公司一年在技术上要投多少钱", TABLE)
    assert "质押" in terms_for("大股东的股票有没有被抵押出去", TABLE)


def test_matching_is_on_bigrams_not_substrings() -> None:
    assert "技术投入" not in "公司一年在技术上要投多少钱"
    assert "研发投入" in terms_for("公司一年在技术上要投多少钱", TABLE)


def test_terms_already_present_are_not_repeated() -> None:
    assert "存货" not in terms_for("存货有多少", TABLE)


def test_rewrite_weight_is_below_full_weight() -> None:
    assert 0 < TABLE.weight < 1


def test_term_groups_are_not_single_characters() -> None:
    assert all(len(term) > 1 for group in TABLE.groups for term in group)
