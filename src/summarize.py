"""GPT 모델로 뉴스 본문을 한 줄 요약."""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

from src.fetch_news import NewsItem

SYSTEM_PROMPT = (
    "너는 한국어 뉴스 한줄 요약가다. 사용자가 준 기사 제목과 본문 일부를 보고 "
    "한 문장(최대 60자)으로 핵심을 요약한다. "
    "낚시성 표현 금지, 객관적 사실 위주. 마침표로 끝낸다."
)


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 환경변수가 비어 있다.")
    return OpenAI(api_key=api_key)


def _get_model() -> str:
    return os.environ.get("OPENAI_MODEL", "gpt-5.5").strip()


def _summarize_one(client: OpenAI, model: str, item: NewsItem) -> str:
    user_msg = f"제목: {item.title}\n\n본문 일부:\n{item.preview or '(본문 미수집)'}"
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_completion_tokens=500,
        )
        text = (resp.choices[0].message.content or "").strip()
        return text.replace("\n", " ")
    except Exception as exc:
        print(f"[WARN] 요약 실패 ({item.title[:30]}): {exc}")
        return item.title[:60]


def summarize_items(items: list[NewsItem], max_workers: int = 6) -> list[NewsItem]:
    """각 뉴스에 한줄요약을 채워서 같은 리스트를 반환."""
    client = _get_client()
    model = _get_model()

    futures = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        for it in items:
            futures[ex.submit(_summarize_one, client, model, it)] = it
        for fut in as_completed(futures):
            it = futures[fut]
            it.preview = fut.result()
    return items
