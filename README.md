# 📰 Daily News Briefing → Telegram

매일 아침 9시(KST)에 네이트 랭킹 뉴스 6개 카테고리(종합/스포츠/연예/경제/사회/IT·과학)의 TOP 10을 크롤링하고, GPT로 한줄 요약한 뒤 텔레그램 봇으로 받아보는 자동화 프로젝트.

## 흐름

```
[네이트 랭킹] → [본문 미리보기] → [GPT 한줄요약] → [텔레그램 메시지]
                          ↑ GitHub Actions cron (매일 09:00 KST)
```

## 구성 파일

| 파일 | 역할 |
|---|---|
| `src/fetch_news.py` | 네이트 6개 카테고리 × TOP 10 + 본문 미리보기 수집 |
| `src/summarize.py` | GPT로 한줄 요약 (병렬 처리) |
| `src/telegram_send.py` | 텔레그램 메시지 포맷 + 전송 |
| `src/main.py` | 오케스트레이션 엔트리 |
| `.github/workflows/daily-briefing.yml` | GitHub Actions cron 정의 |

## 로컬 실행

```bash
uv sync
cp .env.example .env
# .env 파일에 토큰/키 입력
uv run python -m src.main
```

## GitHub Secrets (필수)

GitHub 레포 → Settings → Secrets and variables → Actions → New repository secret 에서 아래 4개를 등록:

| Secret 이름 | 값 |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather에서 받은 봇 토큰 |
| `TELEGRAM_CHAT_ID` | 본인의 chat_id |
| `OPENAI_API_KEY` | OpenAI API 키 |
| `OPENAI_MODEL` | `gpt-5.5` (또는 `gpt-5.4-mini`, `gpt-5.1` 등) |

## 수동 실행 (디버그용)

GitHub Actions 탭 → "Daily News Briefing" → "Run workflow" 클릭.

## 정책 주의

네이트 사이트의 `robots.txt`는 일반 봇 크롤링을 허용하지 않는다. 이 프로젝트는 개인 사용 목적으로 하루 1회 60건 수준의 요청만 발생시키지만, 사이트 정책 변경 시 차단될 수 있으며 약관상 회색지대다. **상업적 이용 금지.**
