# Albion Analytics

Albion Online Gameinfo API의 kill event를 수집해 PostgreSQL에 저장하고, 이후 장비/빌드
단위 통계와 웹 랭킹 화면으로 확장하기 위한 프로젝트입니다.

현재 단계는 **Railway Postgres + 상시 worker 수집 MVP**입니다. 웹 프론트와 공개 API는
아직 포함하지 않습니다.

## Requirements

- Python 3.11+
- PostgreSQL
- 로컬 개발용 Docker Compose 선택 사항

## Install

```powershell
cd C:\Dev\albion-analytics-cursor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
copy .env.example .env
```

## Local Usage

Postgres를 띄우고 스키마를 만든 뒤 한 번 수집합니다.

```powershell
docker compose up -d
albion-init-db
albion-collect-events --once --limit 10
```

상시 수집:

```powershell
albion-collect-events
```

플레이어 샘플 조회:

```powershell
albion-fetch-sample "PlayerName"
```

## Railway Deployment

GitHub 연결과 Railway 배포 절차는 [docs/RAILWAY_DEPLOYMENT.md](docs/RAILWAY_DEPLOYMENT.md)를
참고하세요.

Railway 기본 실행은 다음과 같습니다.

- Dockerfile `CMD`: `python -m albion_analytics.scripts.collect_events`
- 수집기 시작 시 `CREATE TABLE IF NOT EXISTS` 기반 스키마를 자동 적용
- DB: Railway PostgreSQL의 `DATABASE_URL`

## Development

```powershell
ruff check src tests
python -m pytest
```

## Project Notes

- 운영 저장소는 PostgreSQL입니다.
- 이벤트는 `(source_region, event_id)` 기준으로 중복 제거됩니다.
- Gameinfo 장비 canonical key는 표시 이름이 아니라 API의 안정적인 `type` 문자열입니다.
- API 페이로드의 `Version`은 게임 패치 번호가 아니라 payload/schema version으로 취급합니다.
- 패치별 통계는 `kill_events.time_stamp`와 `game_patches` 구간으로 매핑합니다.

자세한 프로젝트 방향과 에이전트 작업 규칙은 [AGENTS.md](AGENTS.md)를 참고하세요.
