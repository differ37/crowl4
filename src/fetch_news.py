"""네이트 랭킹 뉴스 크롤러.

각 카테고리(종합/스포츠/연예/경제/사회/IT/과학)의 TOP 10 뉴스를 수집한다.
관심도 랭킹(`/rank/interest?sc=<코드>&p=day`) 페이지를 사용한다.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

CATEGORIES: dict[str, str] = {
    "종합": "all",
    "스포츠": "spo",
    "연예": "ent",
    "경제": "eco",
    "사회": "soc",
    "IT/과학": "its",
}

BASE_URL = "https://news.nate.com"
RANK_URL_TPL = f"{BASE_URL}/rank/interest?sc={{sc}}&p=day"

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)
TIMEOUT = httpx.Timeout(15.0)
REQUEST_INTERVAL_SEC = 0.8


@dataclass
class NewsItem:
    category: str
    rank: int
    title: str
    url: str
    preview: str = ""


def _http_get(client: httpx.Client, url: str) -> str:
    resp = client.get(url, headers={"User-Agent": UA, "Referer": BASE_URL})
    resp.raise_for_status()
    resp.encoding = resp.encoding or "utf-8"
    return resp.text


def _parse_ranking(html: str, category: str) -> list[NewsItem]:
    """랭킹 페이지 HTML에서 TOP 10 추출. 네이트 마크업 변동에 대비해 여러 셀렉터를 순차 시도."""
    soup = BeautifulSoup(html, "lxml")

    candidate_selectors = [
        "div.postRankSubjectList .mlt01 li",
        "div.mduCluster .mduSubject",
        ".postSubjectList .post",
        ".mlt01 > li",
        "ol.list_news > li",
        "div.rankNewsList li",
        "div.newslist li",
    ]

    posts = []
    for sel in candidate_selectors:
        posts = soup.select(sel)
        if len(posts) >= 5:
            break

    if not posts:
        anchors = soup.select('a[href*="/view/"]')
        seen = set()
        for a in anchors:
            href = a.get("href", "")
            if not href or href in seen:
                continue
            text = a.get_text(strip=True)
            if not text or len(text) < 10:
                continue
            seen.add(href)
            posts.append(a)

    items: list[NewsItem] = []
    rank = 0
    for post in posts:
        if post.name == "a":
            link = post
        else:
            link = post.find("a", href=True)
        if not link:
            continue
        title = link.get_text(strip=True)
        title = re.sub(r"\s+", " ", title)
        if len(title) < 6:
            continue
        href = link.get("href", "")
        if not href:
            continue
        if href.startswith("//"):
            href = "https:" + href
        elif not href.startswith("http"):
            href = urljoin(BASE_URL, href)
        if "/view/" not in href and "/article/" not in href:
            continue
        rank += 1
        items.append(NewsItem(category=category, rank=rank, title=title, url=href))
        if rank >= 10:
            break

    return items


def _extract_article_meta(html: str, max_chars: int = 500) -> tuple[str, str]:
    """기사 본문 페이지에서 (정제된 제목, 본문 미리보기) 추출.

    랭킹 페이지에서 잡힌 제목은 본문 일부가 섞일 수 있어, 본문 페이지의
    og:title 또는 <title>로 다시 덮어쓴다.
    """
    soup = BeautifulSoup(html, "lxml")

    clean_title = ""
    og_title = soup.select_one('meta[property="og:title"]')
    if og_title and og_title.get("content"):
        clean_title = og_title["content"].strip()
    if not clean_title:
        title_tag = soup.find("title")
        if title_tag:
            clean_title = title_tag.get_text(strip=True)
    clean_title = re.sub(r"\s*[:\|\-]\s*네이트.*$", "", clean_title)
    clean_title = re.sub(r"\s+", " ", clean_title).strip()

    candidate_selectors = [
        "#realArtcContents",
        "#articleContetns",
        "#articleContents",
        ".articleCont",
        "#newsContents",
        "article",
    ]
    body = None
    for sel in candidate_selectors:
        body = soup.select_one(sel)
        if body:
            break

    if body:
        for tag in body.select("script, style, table, iframe, .articleAd, .ad"):
            tag.decompose()
        preview = body.get_text(separator=" ", strip=True)
    else:
        og_desc = soup.select_one('meta[property="og:description"]')
        preview = og_desc["content"].strip() if og_desc and og_desc.get("content") else ""

    preview = re.sub(r"\s+", " ", preview)[:max_chars]
    return clean_title, preview


def fetch_all_categories() -> list[NewsItem]:
    """6개 카테고리의 TOP 10 뉴스를 수집. 각 뉴스의 본문 미리보기까지 포함."""
    all_items: list[NewsItem] = []
    with httpx.Client(timeout=TIMEOUT, follow_redirects=True) as client:
        for cat_name, sc in CATEGORIES.items():
            url = RANK_URL_TPL.format(sc=sc)
            try:
                html = _http_get(client, url)
            except httpx.HTTPError as exc:
                print(f"[WARN] {cat_name} 랭킹 페이지 실패: {exc}")
                continue
            items = _parse_ranking(html, cat_name)
            print(f"[INFO] {cat_name}: {len(items)}건 추출")
            for item in items:
                time.sleep(REQUEST_INTERVAL_SEC)
                try:
                    article_html = _http_get(client, item.url)
                    clean_title, preview = _extract_article_meta(article_html)
                    if clean_title:
                        item.title = clean_title
                    item.preview = preview
                except httpx.HTTPError as exc:
                    print(f"[WARN] 본문 추출 실패 ({item.url}): {exc}")
                    item.preview = ""
            all_items.extend(items)
            time.sleep(REQUEST_INTERVAL_SEC)
    return all_items


if __name__ == "__main__":
    results = fetch_all_categories()
    by_cat: dict[str, list[NewsItem]] = {}
    for it in results:
        by_cat.setdefault(it.category, []).append(it)
    for cat, items in by_cat.items():
        print(f"\n=== {cat} ({len(items)}건) ===")
        for it in items:
            print(f"  {it.rank}. {it.title}")
            print(f"     {it.url}")
            if it.preview:
                print(f"     preview: {it.preview[:80]}...")
