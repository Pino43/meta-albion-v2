# GitHub + Railway 배포 가이드

이 가이드는 Albion Analytics 수집기를 GitHub에 올리고, Railway에서
PostgreSQL + 상시 worker로 실행하는 절차입니다. 이번 배포 범위는 웹/API가 아니라
`kill_events`에 Europe, Americas, Asia 3개 리전의 raw kill event를 계속 쌓는
수집 MVP입니다.

## 1. 현재 배포 구조

- GitHub: 이 저장소의 소스 코드 원격 저장소
- Railway PostgreSQL: 운영 DB
- Railway worker 서비스: `albion-collect-events`를 계속 실행하는 수집기
- 수집기 시작 시 안전한 idempotent 스키마 자동 적용

Railway 설정은 저장소 루트의 `railway.toml`에 들어 있습니다.

```toml
[build]
builder = "RAILPACK"
buildCommand = "pip install ."

[deploy]
startCommand = "PYTHONPATH=/app/src python -m albion_analytics.scripts.collect_events"
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 10
```

## 2. 로컬 Git 적용

변경 내용을 확인합니다.

```powershell
git status --short --branch
git diff --stat
```

커밋합니다.

```powershell
git add .
git commit -m "Prepare Railway collector deployment"
```

민감 정보는 커밋하지 않습니다. `.env`, `.venv`, 로컬 DB 파일은 `.gitignore`에 의해 제외됩니다.

## 3. GitHub 원격 저장소 연결

현재 저장소에 원격이 없다면 GitHub에서 새 repository를 만든 뒤 URL을 연결합니다.

```powershell
git remote add origin https://github.com/<OWNER>/<REPO>.git
git push -u origin main
```

이미 원격이 있다면 URL을 확인한 뒤 push만 합니다.

```powershell
git remote -v
git push
```

URL을 잘못 넣었다면 다음처럼 교체합니다.

```powershell
git remote set-url origin https://github.com/<OWNER>/<REPO>.git
```

GitHub CLI를 설치한 환경에서는 다음 방식도 가능합니다.

```powershell
gh repo create <OWNER>/<REPO> --private --source=. --remote=origin --push
```

## 4. Railway 프로젝트 만들기

1. Railway에서 새 프로젝트를 만듭니다.
2. `+ New`에서 PostgreSQL 서비스를 추가합니다.
3. GitHub repository를 Railway 프로젝트에 연결합니다.
4. 코드 서비스는 web server가 아니라 worker로 사용합니다.
5. Railway가 저장소의 `railway.toml`을 읽어 build/pre-deploy/start command를 적용하는지 확인합니다.

Railway CLI를 쓰는 경우:

```powershell
railway login
railway link
railway up
```

## 5. Railway 환경 변수

코드 서비스에 아래 변수를 설정합니다.

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
DATABASE_CONNECT_MAX_RETRIES=10
DATABASE_CONNECT_RETRY_DELAY_SEC=3
COLLECT_REGIONS=europe,americas,asia
COLLECT_POLL_INTERVAL_SEC=60
COLLECT_EVENTS_LIMIT=1000
COLLECT_MAX_PAGES=10
COLLECT_ERROR_BACKOFF_SEC=30
ALBION_RATE_LIMIT_PER_SEC=5
ALBION_HTTP_TIMEOUT_SEC=30
ALBION_HTTP_MAX_RETRIES=3
ALBION_HTTP_RETRY_BASE_DELAY_SEC=1.0
```

Railway의 PostgreSQL 서비스명이 `Postgres`가 아니라면 `DATABASE_URL` 참조 이름을 실제
서비스명에 맞춥니다. 예를 들어 서비스명이 `Albion DB`라면 Railway UI에서 제공하는 변수
참조 문법을 그대로 선택해 넣습니다.

## 6. 배포 확인

배포 로그에서 아래 흐름을 확인합니다.

```text
INFO Applying database schema before collection
INFO Database schema applied (...)
INFO collection_region region=europe cursor=... fetched=... inserted=... skipped_invalid=... duration_sec=...
INFO collection_region region=americas cursor=... fetched=... inserted=... skipped_invalid=... duration_sec=...
INFO collection_region region=asia cursor=... fetched=... inserted=... skipped_invalid=... duration_sec=...
INFO collection_round status=success fetched=... inserted=... skipped_invalid=... patch_updated=... duration_sec=...
```

수집기가 일시적인 API 오류나 네트워크 오류를 만나면 종료하지 않고
`COLLECT_ERROR_BACKOFF_SEC` 이후 재시도합니다. Railway 재배포나 중지 신호를 받으면 현재
라운드 후 DB 연결을 닫고 종료합니다.

배포가 실패하면 Railway의 deploy log에서 start command 출력을 먼저 확인합니다. 자주 나는
원인은 다음입니다.

- `DATABASE_URL is not set`: 코드 서비스에 `DATABASE_URL=${{Postgres.DATABASE_URL}}`가 없습니다.
- `could not translate host name` 또는 connection refused: Postgres 서비스가 준비 중이거나 변수 참조가 잘못됐습니다. 이 프로젝트는 기본 10회, 3초 간격으로 재시도합니다.
- `No module named albion_analytics`: 최신 `railway.toml`이 배포되지 않았거나 Railway root directory가 저장소 루트가 아닙니다. 현재 설정은 `pip install .`와 `PYTHONPATH=/app/src`를 함께 사용합니다.

이전 버전처럼 Railway `preDeployCommand`에서 스키마를 만들지 않습니다. Railway 배포 단계의
pre-deploy 실패를 피하기 위해 collector 시작 시 스키마를 적용합니다. 수동 초기화가 필요하면
Railway shell 또는 로컬에서 `python -m albion_analytics.scripts.init_db`를 실행할 수 있습니다.

## 7. DB 검증 SQL

Railway PostgreSQL Query 탭이나 외부 DB 클라이언트에서 확인합니다.

```sql
SELECT source_region, count(*), max(time_stamp)
FROM kill_events
GROUP BY source_region
ORDER BY source_region;

SELECT source_region, last_max_event_id, last_poll_at
FROM ingestion_cursors
ORDER BY source_region;

SELECT id, started_at, finished_at, status, total_fetched, total_inserted,
       total_skipped_invalid, patch_rows_updated, error_message
FROM collector_runs
ORDER BY started_at DESC
LIMIT 20;
```

정상 상태에서는 `kill_events`와 `ingestion_cursors`에 `europe`, `americas`, `asia`가
나타나고, `collector_runs`에 `success` 라운드가 주기적으로 추가됩니다.

## 8. 로컬 검증

기존 `.venv`가 깨져 있다면 다시 만듭니다.

```powershell
cd C:\Dev\albion-analytics-cursor
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

검증 명령:

```powershell
ruff check src tests
python -m pytest
docker compose up -d
copy .env.example .env
albion-init-db
albion-collect-events --once --limit 10
```

로컬 Postgres에서도 7장의 SQL로 데이터 삽입을 확인할 수 있습니다.

## 9. 운영 메모

- Railway Cron은 이번 구성에서 사용하지 않습니다. Cron은 최소 5분 간격이고 실행 후 종료해야 하므로,
  지금 목표인 상시 수집에는 worker가 맞습니다.
- 기존 DB 데이터는 삭제하지 않습니다. 스키마는 `CREATE TABLE IF NOT EXISTS`,
  `CREATE INDEX IF NOT EXISTS` 중심으로 안전하게 확장합니다.
- 장비/빌드 통계 정규화 테이블, 공개 API, 웹 프론트, raw/보정 통계 계산은 다음 단계입니다.
