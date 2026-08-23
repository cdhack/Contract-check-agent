"""Fetch the official Japanese Arbitration Act full text for the local knowledge base."""
from pathlib import Path
import re
from urllib.request import urlopen
from xml.etree import ElementTree

URL = "https://elaws.e-gov.go.jp/api/1/lawdata/415AC0000000138"
TARGET = Path(__file__).resolve().parents[1] / "knowledge_sources" / "jp" / "arbitration_act_full.txt"
TEXT_TAGS = {"LawTitle", "PartTitle", "ChapterTitle", "SectionTitle", "SubsectionTitle", "DivisionTitle", "ArticleCaption", "ArticleTitle", "ParagraphNum", "ParagraphSentence", "ItemTitle", "ItemSentence"}

if __name__ == "__main__":
    with urlopen(URL, timeout=60) as response:
        root = ElementTree.fromstring(response.read())
    lines = ["# 日本仲裁法（官方全文）", ""]
    for element in root.findall(".//LawFullText//*"):
        if element.tag in TEXT_TAGS:
            text = re.sub(r"\s+", " ", "".join(element.itertext())).strip()
            if text and text != lines[-1]: lines.append(text)
    TARGET.write_text("\n".join(lines) + "\n", "utf-8")
    print(f"Saved {len(lines) - 2} legal text elements to {TARGET}")
