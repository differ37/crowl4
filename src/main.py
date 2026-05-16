"""매일 9시 KST 실행되는 뉴스 브리핑 오케스트레이션 엔트리포인트."""

from __future__ import annotations

import sys

from dotenv import load_dotenv

from src.fetch_news import fetch_all_categories
from src.summarize import summarize_items
from src.telegram_send import send_briefing


def main() -> int:
    load_dotenv()
    print("[STEP 1] 네이트 랭킹 뉴스 수집 시작")
    items = fetch_all_categories()
    if not items:
        print("[FATAL] 수집된 뉴스가 0건. 페이지 구조 변경 가능성 — 종료.")
        return 1
    print(f"[STEP 1 완료] 총 {len(items)}건 수집")

    print("[STEP 2] GPT 한줄요약 생성")
    items = summarize_items(items)
    print("[STEP 2 완료]")

    print("[STEP 3] 텔레그램 전송")
    send_briefing(items)
    print("[STEP 3 완료] 모든 작업 종료")
    return 0


if __name__ == "__main__":
    sys.exit(main())
