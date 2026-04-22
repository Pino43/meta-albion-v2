# AGENTS.md — Albion Analytics

이 문서는 사람과 AI 코딩 에이전트가 동일한 전제로 작업하도록 정리한 프로젝트 가이드입니다.

## 목표

- 알비온 온라인 **킬·데스(이벤트)** 데이터 수집 → **빌드(머리·가슴·신발·무기·망토 등) 단위** 집계·통계.
- 이후 웹에서 op.gg / MetaTFT 스타일로 **티어·순위** 표시. **보정 적용/원시(raw)** 두 뷰는 프론트에서 토글할 계획.
- **아이템 파워(IP)**, **페임**, **킬 참여 인원(솔로/파티)** 등은 분석 단계에서 가중·필터로 확장.

## 제품·데이터 결정 (확정)

- **저장소**: **PostgreSQL**을 운영 기준 저장소로 둔다. (로컬 프로토타입만 SQLite 등을 써도 됨.)
- **페이지 단위**: **장비 하나(단일 슬롯 아이템)** 가 하나의 상세 페이지다. URL·DB 조인 키는 게임/API와 동일한 **안정적인 식별자**를 쓴다. Gameinfo 장비 슬롯에는 보통 `type` 문자열(티어·템플릿이 들어간 ID)이 오므로 **canonical 키 = `type`**, 화면에 보이는 **이름은 아이템 메타(또는 로컬 매핑)로 표시**한다. “이름만”으로 키를 쓰지 않는다(번역·표기 차이로 중복·누락이 생김).
- **장비 페이지 안에 넣을 통계(예시)**: 해당 장비가 **킬(가해자) 관점** 등 선택한 관점에서 잡힌 이벤트만 필터한 뒤, **티어(및 인챈트) 분포**, **함께 많이 쓰인 빌드(다른 슬롯 조합)**, 필요 시 **서버(리전)별 / 전체** 탭 등.
- **수집**: 가능한 한 넓게 수집한 뒤, **1v1·2v2·파티 규모** 등은 집계·조회 단계에서 필터로 적용한다.

## 로컬 PC에서 수집할 때 (전원·보관)

- **수집기(`albion-collect-events`)는 그 프로세스가 돌아가는 동안만** API를 폴링한다. **PC를 끄거나 잠자기**에 들어가면 그 시간에는 **새 데이터가 들어오지 않는다**(타임라인에 빈 구간이 생김). 알비온 API가 과거 구간을 무료로 전부 돌려주지 않을 수 있어, **끄기 전까지 쌓인 구간만** 확실히 갖는 셈이다.
- **이미 Postgres에 들어간 데이터**는 전원을 꺼도 **디스크에 남는다**(Docker 볼륨·로컬 데이터 디렉터리 등). `docker compose down`만 해도 **볼륨을 지우지 않는 한** 데이터는 유지된다. 장기 보관은 **`pg_dump` 백업** 또는 볼륨/디스크 백업을 권장한다.
- **배포 없이도** “끄지 않는 어딘가”에만 옮기면 상시 수집에 가까워진다: 저렴한 **VPS**, 집에서 켜 두는 **미니 PC/NAS**, **클라우드 VM** 등에 동일한 Postgres + 수집기를 두고 `DATABASE_URL`만 맞추면 된다. 나중에 웹을 올릴 때 **같은 DB를 그대로 쓰거나 `pg_dump`로 이전**하면 된다.

## 스택 (현재)

- **Python 3.11+**, 패키지 이름 `albion-analytics`, 소스는 `src/albion_analytics/`.
- HTTP: `httpx`, 설정: `pydantic-settings`, 스키마: `pydantic` v2, DB: **psycopg** 3 (PostgreSQL).
- 린트: `ruff`, 테스트: `pytest` + `pytest-asyncio`.

## 디렉터리

| 경로 | 역할 |
|------|------|
| `src/albion_analytics/` | 라이브러리: API 클라이언트, 모델, 수집, 분석 |
| `src/albion_analytics/api/` | Gameinfo HTTP 클라이언트(재시도·속도 제한) |
| `src/albion_analytics/models/` | 킬 이벤트·장비 등 Pydantic 모델 |
| `src/albion_analytics/ingestion/` | 수집: 플레이어 킬, **전역 `/events` 폴링**(`event_feed`) 등 |
| `src/albion_analytics/storage/` | Postgres 스키마·이벤트 upsert(중복 제거) |
| `src/albion_analytics/analysis/` | 집계·티어 계산 등(초기에는 스텁) |
| `scripts/` | 일회성·운영 스크립트(선택) |
| `tests/` | 단위 테스트 |
| `data/` | 로컬 DB·캐시(`.gitignore`, 커밋하지 않음) |

## 알비온 Gameinfo 베이스 URL (지역)

환경 변수 `ALBION_GAMEINFO_BASE_URL`로 지정. 끝에 `/api/gameinfo`까지 포함.

- Europe: `https://gameinfo.albiononline.com/api/gameinfo`
- Americas: `https://gameinfo-ams.albiononline.com/api/gameinfo`
- Asia: `https://gameinfo-sgp.albiononline.com/api/gameinfo`

비공식 API이므로 호스트·경로 변경 가능성 있음 — 실패 시 커뮤니티/포럼 최신 정보 확인.

### 킬 이벤트 JSON의 `Version` vs 게임 패치

- 응답에는 **`TimeStamp`**, **`EventId`**, **`Version`(숫자, 예: 4)** 등이 있다.
- **`Version`은 API 페이로드/스키마 버전**으로 보는 것이 맞고, **게임 패치 이름·번호와 동일하지 않다.**
- **패치별 통계**는 **`kill_events.time_stamp` + `game_patches` 테이블**(패치별 `starts_at` / `ends_at`)으로 나눈다. 패치 출시 시 행을 추가하고, 수집 루프 끝에서 `assign_patches_from_ranges`가 `patch_id`를 채운다. 구간은 **겹치지 않게** 유지하는 것이 안전하다.

## 명령 (Windows PowerShell 예시)

```powershell
cd c:\Dev\albion-analytics-cursor
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
ruff check src tests
pytest
albion-fetch-sample "PlayerName"

# Postgres (예: docker compose up -d 후)
albion-init-db
albion-collect-events --once
# 지속 수집(기본 간격은 COLLECT_POLL_INTERVAL_SEC)
albion-collect-events
```

## 코딩 규칙

- 요청은 `GameinfoClient`를 경유하고, 밖에서 `httpx`를 직접 난사하지 않기.
- API JSON은 버전에 따라 필드가 빠질 수 있음 → 모델은 **Optional**·`model_config`로 느슨하게, 필요 시 `extra` 허용 영역 명시.
- 새 기능은 **테스트 또는 스크립트로 재현 가능**하게 유지.
- 사용자 규칙: 불필요한 대규모 리팩터·무관 파일 수정 금지.

## Railway read-only access for tests/debugging

- Railway 운영 DB를 자동 테스트, 디버깅, 데이터 분포 확인에 연결할 때는 운영 쓰기 계정 `DATABASE_URL`을 직접 사용하지 않는다.
- 가능하면 Railway Postgres에 **read-only 전용 계정**을 따로 만들고, 로컬 또는 CI에서는 그 계정의 연결 문자열만 사용한다.
- 권장 환경 변수 이름: `RAILWAY_READONLY_DATABASE_URL`
- read-only 계정은 최소 권한 원칙을 따른다.
  - `CONNECT` on database
  - `USAGE` on schema `public`
  - `SELECT` on existing tables
  - `ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES`
  - `ALTER ROLE ... SET default_transaction_read_only = on`
- 에이전트가 Railway에 연결할 때는, 특별한 요청이 없는 한 **조회 전용 SQL과 read-only 연결만** 사용한다.

## Gameinfo `/events` quirks discovered in production

- 현재 확인된 운영 데이터와 라이브 샘플 기준으로, Gameinfo `/events`의 공간 정보는 매우 거칠 수 있다.
  - `KillArea`가 `OPEN_WORLD`로 대량 유입될 수 있다.
  - `Location`은 `null`일 수 있다.
  - 따라서 현재 파이프라인에서는 정확한 개별 존 이름보다 **콘텐츠 대분류** 중심 분류를 우선한다.
- `KillArea=OPEN_WORLD`는 `unknown`으로 버리지 말고 `open_world` content type으로 분류한다.
- 실제 API 샘플에서 `Participants` 배열에 `Killer` 본인이 포함될 수 있었다.
  - kill-side 인원수 계산 시 killer를 한 번 더 더하지 않는다.
  - loadout normalization에서도 killer를 `participant`로 중복 저장하지 않는다.
- Gameinfo 응답 구조가 달라진 정황이 있으면 샘플 이벤트를 다시 확인하고 extractor/classifier version을 올려 backfill 가능하게 유지한다.

## 웹 프론트

아직 포함하지 않음. 추가 시 `apps/web` 또는 별도 저장소로 두고, 이 패키지는 **집계 결과(DB/API)** 를 제공하는 쪽으로 연결하면 됨.

## 열린 결정 사항

- 킬 스트림 소스·크롤 전략: 전역 이벤트 폴링 vs 시드 플레이어 확장 등(부하·정책).
- 보정 수식: IP·페임 정규화는 수식 확정 후 `analysis`에 반영.
- 장비 페이지의 “기본 관점”: 킬(가해자) 위주 vs 데스(피해자) 위주 — 둘 다 탭으로 줄지, 하나만 기본으로 할지.
