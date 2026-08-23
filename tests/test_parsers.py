import pytest
from app.parsers import ParseError, parse_contract

def test_parse_txt_keeps_locations():
    result = parse_contract("contract.txt", "第一条\n第二条".encode())
    assert result.text == "第一条\n第二条" and result.locations == ["第 1 行", "第 2 行"]

def test_rejects_unsupported_file():
    with pytest.raises(ParseError): parse_contract("contract.xlsx", b"data")
