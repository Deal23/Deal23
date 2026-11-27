#!/usr/bin/env python3
"""Update README badges only after a complete, validated Scholar response."""

from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

URL = "https://scholar.google.com/citations?user=GUH-kwcAAAAJ&hl=en&pagesize=100"
PAPERS = {
    "10.1002/mgea.70091": "machine learning potential for ga",
    "10.1007/s10853-025-11121-z": "tree model",
    "10.1080/19475411.2024.2385349": "self healing liquid metals",
    "10.1002/adma.74076": "liquid metal composites enabled",
}
README = Path(__file__).resolve().parents[1] / "README.md"


def normalize(value):
    return " ".join(re.sub(r"[^a-z0-9]+", " ", value.lower()).split())


class ScholarParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.total = []
        self.rows = []
        self.row = None
        self.capture = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get("class", "").split()
        if tag == "tr" and "gsc_a_tr" in classes:
            self.row = {"title": "", "citations": "", "has_citations": False}
        elif tag == "td" and "gsc_rsb_std" in classes:
            self.capture = "total"
            self.total.append("")
        elif self.row is not None and tag == "a" and "gsc_a_at" in classes:
            self.capture = "title"
        elif self.row is not None and tag == "td" and "gsc_a_c" in classes:
            self.row["has_citations"] = True
            self.capture = "citations"

    def handle_data(self, data):
        if self.capture == "total":
            self.total[-1] += data
        elif self.capture and self.row is not None:
            self.row[self.capture] += data

    def handle_endtag(self, tag):
        if (tag == "a" and self.capture == "title") or (tag == "td" and self.capture in ("total", "citations")):
            self.capture = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def parse(html):
    parser = ScholarParser()
    parser.feed(html)
    if not parser.total or not parser.total[0].strip().replace(",", "").isdigit():
        raise ValueError("Scholar total citations missing or invalid")
    result = {"total": int(parser.total[0].strip().replace(",", ""))}
    for doi, title in PAPERS.items():
        matches = [row for row in parser.rows if normalize(title) in normalize(row["title"])]
        if len(matches) != 1 or not matches[0]["has_citations"]:
            raise ValueError(f"Expected one complete Scholar row for {doi}, found {len(matches)}")
        count = matches[0]["citations"].strip().replace(",", "")
        if count and not count.isdigit():
            raise ValueError(f"Invalid citation count for {doi}")
        result[doi] = int(count or 0)
    return result


def update_readme(text, counts):
    total_url = f'https://img.shields.io/badge/Google%20Scholar%20citations-{counts["total"]}-blue'
    text, replaced = re.subn(r'src="https://img\.shields\.io/badge/Google%20Scholar%20citations-[^"]+"(?= alt="Google Scholar total citations")', f'src="{total_url}"', text)
    if replaced != 1:
        raise ValueError("Expected one total citations badge")
    lines = text.splitlines(keepends=True)
    for doi in PAPERS:
        indices = [i for i, line in enumerate(lines) if f"https://doi.org/{doi}" in line]
        if len(indices) != 1:
            raise ValueError(f"Expected one README entry for {doi}")
        index = indices[0]
        url = f'https://img.shields.io/badge/citations-{counts[doi]}-blue'
        lines[index], replaced = re.subn(r'!\[citations\]\(https://img\.shields\.io/badge/citations-[^)]+\)', f'![citations]({url})', lines[index])
        if replaced != 1:
            raise ValueError(f"Expected one citations badge for {doi}")
    return "".join(lines)


def main():
    request = Request(URL, headers={"User-Agent": "Mozilla/5.0 (compatible; citation-update/1.0)"})
    with urlopen(request, timeout=30) as response:
        html = response.read().decode("utf-8")
    updated = update_readme(README.read_text(encoding="utf-8"), parse(html))
    README.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Citation update failed; existing badges preserved: {error}", file=sys.stderr)
        sys.exit(1)
