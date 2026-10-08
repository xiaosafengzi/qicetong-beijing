import pytest

from qicetong.model import validate_candidates


def test_fabricated_quote_is_discarded():
    asset={"id":"a","suffix":".txt","chunks":[{"locator":"第1段","text":"2025年度销售收入100万元。"}]}
    output={"fields":[{"field":"sales_2025","value":100,"unit":"万元","period":"2025","quote":"2025年度销售收入100万元。"},
                      {"field":"rd_2025","value":10,"unit":"万元","period":"2025","quote":"研发费用10万元"}]}
    proposals,_=validate_candidates(output,asset)
    assert len(proposals)==1 and proposals[0]["field"]=="sales_2025"
    assert proposals[0]["state"]=="pending"


def test_image_transcript_never_claims_verified_ocr():
    asset={"id":"a","suffix":".png","chunks":[]}
    proposals,chunks=validate_candidates({"recognized_text":"职工总数80人","fields":[{"field":"employees","value":80,"unit":"人","period":"2025","quote":"职工总数80人"}]},asset)
    assert "草稿" in chunks[0]["locator"] and proposals[0]["state"]=="pending"


def test_financial_field_without_year_is_discarded():
    asset={"id":"a","suffix":".txt","chunks":[{"locator":"第1段","text":"销售收入100万元。"}]}
    proposals,_=validate_candidates({"fields":[{"field":"sales","value":100,"quote":"销售收入100万元。"}]},asset)
    assert not proposals
