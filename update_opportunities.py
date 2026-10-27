
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date
from html import unescape
from pathlib import Path

RSS_URL = (
    "https://www.k-startup.go.kr/"
    "web/contents/rss/bizpbanc-ongoing.do"
)

def text_of(element, name):
    for child in element.iter():
        if child.tag.split("}")[-1] == name:
            return "".join(child.itertext()).strip()
    return ""

def clean_text(value):
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", unescape(value)).strip()

def get_deadline(text):
    # 예: 2026-11-06, 2026.11.06
    match = re.search(
        r"(20\d{2})[.-]\s*(\d{1,2})[.-]\s*(\d{1,2})",
        text
    )
    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3))
            )
        except ValueError:
            return None

    # 예: (~11/5), (11.05까지)
    match = re.search(
        r"~\s*(\d{1,2})[./-]\s*(\d{1,2})",
        text
    )
    if match:
        try:
            month = int(match.group(1))
            day = int(match.group(2))
            year = date.today().year

            # 연말에 다음 해 마감 공고가 나오는 경우를 고려
            if date.today().month == 12 and month == 1:
                year += 1

            return date(year, month, day)
        except ValueError:
            return None

    return None

def main():
    request = urllib.request.Request(
        RSS_URL,
        headers={"User-Agent": "OpportunityFinder/1.0"}
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)
    today = date.today()
    opportunities = []
    seen_links = set()

    for item in root.iter():
        if item.tag.split("}")[-1] not in ("item", "entry"):
            continue

        title = text_of(item, "title")
        link = text_of(item, "link")
        description = clean_text(text_of(item, "description"))

        if not link:
            for child in item:
                if child.tag.split("}")[-1] == "link":
                    link = child.attrib.get("href", "")
                    if link:
                        break

        if not title or not link or link in seen_links:
            continue

        seen_links.add(link)
        deadline = get_deadline(title + " " + description)

        # 마감일을 알아낼 수 있고 이미 지났다면 제외
        if deadline and deadline < today:
            continue

        opportunities.append({
            "title": title,
            "url": link,
            "description": description,
            "deadline": deadline.isoformat() if deadline else None,
            "category": "창업",
            "source": "K-Startup"
        })

    output = Path("opportunities.json")
    output.write_text(
        json.dumps(
            opportunities,
            ensure_ascii=False,
            indent=2
        ),
        encoding="utf-8"
    )

    print(f"수집 완료: {len(opportunities)}개 공고")

if __name__ == "__main__":
    main()
