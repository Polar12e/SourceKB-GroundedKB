import json

import pymupdf

from workers.parser.extract_pdf import extract_pages, write_pages_jsonl


def make_pdf(path) -> None:
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "GroundedKB parser test")
    page2 = document.new_page()
    page2.insert_text((72, 72), "second page")
    document.save(path)
    document.close()


def test_extract_pages(tmp_path) -> None:
    pdf = tmp_path / "sample.pdf"
    make_pdf(pdf)

    pages = extract_pages(pdf)

    assert [page.page for page in pages] == [1, 2]
    assert "GroundedKB" in pages[0].text
    assert "second page" in pages[1].text


def test_write_pages_jsonl(tmp_path) -> None:
    pdf = tmp_path / "sample.pdf"
    make_pdf(pdf)
    pages = extract_pages(pdf)
    output = tmp_path / "pages.jsonl"

    write_pages_jsonl("demo-2024", pages, output)

    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert records[0] == {
        "document_id": "demo-2024",
        "page": 1,
        "text": records[0]["text"],
    }
    assert "GroundedKB" in records[0]["text"]
