# 오늘의 K랭킹

다이소·올리브영(국내/글로벌) 인기 순위 TOP 100을 매일 정리하는 정적 사이트.

- `fetch.py` — Apify Actor(daiso-ranking-scraper, oliveyoung-ranking-scraper)를 실행해 `data/<목록>/<날짜>.json` 저장. 순위·상품명·브랜드·가격·평점·리뷰 수·원본 링크만 남긴다(이미지·리뷰 본문 없음).
- `build.py` — `data/`에서 `docs/`로 HTML 생성. 순위 변동은 직전 스냅샷과 비교.
- `.github/workflows/daily.yml` — 매일 09:30 KST 실행. 저장소 Secrets에 `APIFY_TOKEN` 필요.
- 로컬: `python3 fetch.py && python3 build.py` (apify CLI 로그인 사용).
