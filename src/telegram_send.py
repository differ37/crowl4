"""텔레그램 봇으로 브리핑 메시지 전송."""

from __future__ import annotations

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx

from src.fetch_news import NewsItem

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
KST = ZoneInfo("Asia/Seoul")
MAX_MSG_LEN = 3800


def _env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"{name} 환경변수가 비어 있다.")
    return value


def _escape(text: str) -> str:
    """텔레그램 HTML 파싱 모드에서 안전하도록 메타문자 이스케이프."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]
DIVIDER = "━━━━━━━━━━━━━━"


def _format_messages(items: list[NewsItem]) -> list[str]:
    """카테고리별로 묶어 텔레그램 메시지 청크 리스트로 변환.

    레이아웃: 상단 헤더 → 카테고리별 블록(구분선 + 제목 + 번호별 뉴스).
    각 뉴스는 [번호. 제목(링크)] 다음 줄에 들여쓰기된 요약문 한 줄.
    """
    by_cat: dict[str, list[NewsItem]] = {}
    for it in items:
        by_cat.setdefault(it.category, []).append(it)

    now = datetime.now(KST)
    date_str = f"{now.month}/{now.day} ({WEEKDAY_KO[now.weekday()]}) {now.strftime('%H:%M')}"
    header = f"🗞 <b>네이트 뉴스 브리핑</b>\n<i>{date_str} KST</i>\n"

    chunks: list[str] = []
    current = header

    for cat, news_list in by_cat.items():
        block = f"\n{DIVIDER}\n📰 <b>{cat}</b>\n{DIVIDER}\n\n"
        for it in sorted(news_list, key=lambda x: x.rank):
            title = _escape(it.title)
            summary = _escape(it.preview or "")
            block += f"<b>{it.rank}.</b> <a href=\"{it.url}\">{title}</a>\n"
            if summary:
                block += f"    {summary}\n"
            block += "\n"

        if len(current) + len(block) > MAX_MSG_LEN:
            chunks.append(current.rstrip())
            current = block
        else:
            current += block

    if current.strip():
        chunks.append(current.rstrip())
    return chunks


def send_briefing(items: list[NewsItem]) -> None:
    token = _env("TELEGRAM_BOT_TOKEN")
    chat_id = _env("TELEGRAM_CHAT_ID")
    api_url = TELEGRAM_API.format(token=token)

    messages = _format_messages(items)
    with httpx.Client(timeout=15.0) as client:
        for i, msg in enumerate(messages, 1):
            resp = client.post(
                api_url,
                json={
                    "chat_id": chat_id,
                    "text": msg,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
            )
            if resp.status_code != 200:
                print(f"[ERROR] 메시지 {i} 전송 실패: {resp.status_code} {resp.text}")
                resp.raise_for_status()
            else:
                print(f"[INFO] 메시지 {i}/{len(messages)} 전송 완료")
