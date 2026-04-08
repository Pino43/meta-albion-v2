# Albion Analytics

알비온 온라인 킬·데스 데이터를 수집·분석해 무기·장비 빌드 통계(티어, 순위 등)를 제공하는 프로젝트입니다.  
현재 단계는 **데이터 수집·분석 파이프라인** 중심이며, 웹 프론트는 이후 단계에서 추가합니다.

## 요구 사항

- Python 3.11+

## 설치

```bash
cd c:\Dev\albion-analytics-cursor
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
copy .env.example .env
```

## 환경 변수

`.env`에 `ALBION_GAMEINFO_BASE_URL` 등을 설정합니다. 지역(유럽/미국/아시아)별 Gameinfo 호스트는 [AGENTS.md](./AGENTS.md)를 참고하세요.

## 사용

샘플로 플레이어 킬 이벤트를 가져와 콘솔에 요약합니다(플레이어 이름은 알비온 정확한 닉네임).

```bash
albion-fetch-sample "플레이어이름"
```

## 개발

```bash
ruff check src tests
ruff format src tests
pytest
```

## API 참고

알비온은 공개된 공식 REST 문서가 거의 없고, 웹/게임에서 쓰는 **Gameinfo** 엔드포인트를 커뮤니티가 활용합니다. 응답 스키마는 변경될 수 있으므로 `albion_analytics.models`의 Pydantic 모델은 실제 응답을 보며 조정하세요.

## AI 에이전트

- [AGENTS.md](./AGENTS.md): 아키텍처·명령·규칙(모든 도구 공통 기준).
- [CLAUDE.md](./CLAUDE.md): Claude Code 등에서 `AGENTS.md`를 가리키는 짧은 진입점.
