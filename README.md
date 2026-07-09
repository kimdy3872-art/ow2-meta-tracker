# Overwatch 2 경쟁전 메타 분석 대시보드

오버워치 2 경쟁전 통계, 영웅 퍼크, 공식 패치노트를 수집해 Streamlit으로 시각화하는 데이터 분석 프로젝트입니다. 티어별/포지션별 승률, 픽률, 밴률을 기반으로 영웅 랭크를 계산하고, 저장된 스냅샷으로 메타 변화 추이를 확인합니다.

이 README는 사람뿐 아니라 다른 AI 에이전트가 프로젝트를 이어받을 때도 빠르게 맥락을 파악할 수 있도록 작성되어 있습니다.

---

## 프로젝트 한눈에 보기

- **앱 유형**: Streamlit 멀티페이지 대시보드
- **주요 데이터**: 오버워치 2 경쟁전 영웅 통계, OW Perks 영웅 퍼크, Blizzard 공식 패치노트
- **핵심 산출물**: `data/latest/latest_tier.parquet`, `data/latest/latest_perks.parquet`, `data/patch_notes/*.json`
- **주요 실행 파일**: `main.py`는 대시보드, `update.py`는 데이터 수집/가공
- **기본 언어**: 한국어 UI와 한국어 데이터 라벨

---

## 주요 기능

| 페이지 | 파일 | 설명 |
|---|---|---|
| 메인 | `main.py` | 티어, 포지션, 영웅 필터와 S/A/B/C/D 랭크 테이블, 메타 유형 라벨, 최신 패치노트/AI 분석 요약 |
| 픽률/승률 분포 | `pages/1_pick_win_distribution.py` | 선택 티어/포지션 기준 픽률, 승률, 밴률 3D 분포 시각화 |
| 영웅 시계열 | `pages/2_hero_trends.py` | 주간 스냅샷과 최신 데이터를 합쳐 영웅별 승률, 픽률, 밴률, 종합 점수 추이 확인 |
| 영웅 상세 | `pages/3_hero_detail.py` | 특정 영웅의 티어별 지표, 전장별 성능, 퍼크 선호도, 패치 영향 정보 확인 |

---

## 기술 스택

| 분류 | 라이브러리/도구 |
|---|---|
| 대시보드 | Streamlit |
| 데이터 처리 | Pandas, NumPy, PyArrow |
| 시각화 | Plotly |
| 브라우저 수집 | Selenium, Chrome/Chromium |
| 로컬 AI 분석 | Ollama API, 선택 기능 |
| 자동화 | GitHub Actions, macOS launchd 스크립트 |

---

## 프로젝트 구조

```text
.
├── main.py
├── pages/
│   ├── 1_pick_win_distribution.py
│   ├── 2_hero_trends.py
│   └── 3_hero_detail.py
├── app_data.py
├── ui.py
├── update.py
├── requirements.txt
├── main.yml
├── scripts/
│   ├── LOCAL_AI_PATCH_AUTOMATION.md
│   ├── com.da.overwatch.ai-patch.plist
│   └── run_local_ai_patch_update.sh
└── data/
    ├── latest/
    │   ├── latest_tier.parquet
    │   ├── latest_perks.parquet
    │   └── rank_diagnostics.json
    ├── history/
    │   ├── daily/year=YYYY/month=MM/tier_snapshot.parquet
    │   └── weekly/year=YYYY/week=WW/tier_snapshot.parquet
    └── patch_notes/
        ├── patch_notes.json
        └── patch_ai_analysis.json
```

### 주요 파일 역할

- `main.py`: Streamlit 진입점입니다. 메인 대시보드와 최신 패치 인텔리전스 블록을 렌더링합니다.
- `pages/*.py`: Streamlit 멀티페이지 화면입니다.
- `app_data.py`: 대시보드에서 쓰는 데이터 로딩, 라벨 번역, 영웅/맵 이미지 URL 보조 함수가 모여 있습니다.
- `ui.py`: 전역 다크 테마, 상단 네비게이션, 공통 페이지 히어로 UI를 정의합니다.
- `update.py`: 경쟁전 통계, 퍼크, 패치노트, 패치 AI 분석을 수집/가공/저장하는 핵심 배치 스크립트입니다.
- `main.yml`: 매일 데이터를 갱신하는 GitHub Actions 워크플로 예시입니다. 일반적인 저장소에서는 `.github/workflows/main.yml` 위치에 두는 것을 권장합니다.
- `scripts/LOCAL_AI_PATCH_AUTOMATION.md`: 로컬 Ollama 기반 패치 분석 자동화 운영 문서입니다.

---

## 빠른 시작

### 1. 가상환경 생성

```bash
python3 -m venv venv
source venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. 패키지 설치

```bash
pip install -r requirements.txt
```

### 3. 대시보드 실행

```bash
streamlit run main.py
```

브라우저에서 `http://localhost:8501`에 접속합니다.

---

## 데이터 갱신

`update.py` 하나로 모든 수집 작업을 실행합니다.

### 경쟁전 통계만 갱신

```bash
python update.py
# 또는
python update.py --mode stats
```

저장 결과:

- `data/latest/latest_tier.parquet`: 최신 경쟁전 통계
- `data/history/daily/year=YYYY/month=MM/tier_snapshot.parquet`: 일별 스냅샷
- `data/history/weekly/year=YYYY/week=WW/tier_snapshot.parquet`: 주간 스냅샷
- `data/latest/rank_diagnostics.json`: 랭크 산식 진단 리포트

주간 스냅샷은 기본적으로 월요일에 생성됩니다. `WEEKLY_SNAPSHOT_WEEKDAY` 환경변수로 기준 요일을 바꿀 수 있습니다. Python `weekday()` 기준이라 월요일은 `0`, 일요일은 `6`입니다.

### 영웅 퍼크만 갱신

```bash
python update.py --mode perks
python update.py --mode perks --max-heroes 5
python update.py --mode perks --locale ko
python update.py --mode perks --headed
```

저장 결과:

- `data/latest/latest_perks.parquet`

### 패치노트와 AI 분석 갱신

```bash
python update.py --mode patch
```

저장 결과:

- `data/patch_notes/patch_notes.json`
- `data/patch_notes/patch_ai_analysis.json`

패치노트는 Blizzard 공식 패치노트 페이지를 읽어 최신 패치와 최신 영웅 밸런스 패치를 저장합니다. 로컬에 Ollama가 실행 중이면 패치 영향 분석을 생성하고, 사용할 수 없으면 지표 기반 fallback 분석을 저장합니다.

### 전체 갱신

```bash
python update.py --mode all
```

경쟁전 통계, 퍼크, 패치노트/AI 분석을 한 번에 갱신합니다.

---

## 주요 환경변수

| 환경변수 | 기본값 | 설명 |
|---|---:|---|
| `MAX_WORKERS` | `2` | Selenium 기반 퍼크 수집 병렬 작업 수 |
| `TASK_RETRIES` | `3` | 수집 작업 재시도 횟수 |
| `DRIVER_PAGE_LOAD_TIMEOUT` | `75` | Chrome 페이지 로드 제한 시간(초) |
| `DRIVER_SCRIPT_TIMEOUT` | `30` | Chrome 스크립트 실행 제한 시간(초) |
| `STATS_GAME_MODE_RQ` | `2` | Blizzard 경쟁전 통계 요청 모드 후보의 우선값 |
| `STATS_GAME_MODE_RQ_CANDIDATES` | `STATS_GAME_MODE_RQ` | 통계 수집 시 순서대로 시도할 `rq` 값 목록 |
| `META_PRESENCE_WEIGHT` | `0.65` | 종합 점수에서 존재감 축 가중치 (성능 축은 1 - 이 값) |
| `PRESENCE_BAN_WEIGHT` | `1.0` | 존재감 축에서 밴률 가중치 β. 과열 감시 지표가 지속 초과하면 0.5 하향 검토 |
| `WEEKLY_SNAPSHOT_WEEKDAY` | `0` | 주간 스냅샷 생성 요일 |
| `ENABLE_OLLAMA_ANALYSIS` | 로컬 `1`, GitHub Actions `0` | Ollama 패치 분석 사용 여부 |
| `OLLAMA_MODEL` | `qwen3:14b` | 패치 분석에 사용할 Ollama 모델 |
| `OLLAMA_GENERATE_URL` | `http://localhost:11434/api/generate` | Ollama generate API URL |
| `OLLAMA_TIMEOUT` | `90` | Ollama 응답 제한 시간(초) |
| `FORCE_PATCH_AI_ANALYSIS` | `0` | 기존 분석이 있어도 강제 재생성 |

---

## 데이터 컬럼 및 저장 구조

### 경쟁전 통계 컬럼

| 컬럼 | 설명 |
|---|---|
| `hero`, `role`, `data_tier` | 영웅, 역할, 경쟁전 티어 |
| `map`, `map_name`, `update_date` | 맵 ID, 맵 표시명, 수집일 |
| `win_rate`, `pick_rate`, `ban_rate` | 승률, 픽률, 밴률 |
| `win_rate_z`, `pick_rate_log`, `pick_rate_z`, `ban_rate_log`, `ban_rate_z` | 정규화 지표 |
| `presence_score` | 메타 존재감 축: `z(log1p(pick_rate + β×ban_rate))` |
| `shrunk_win_rate` | 픽률 가중으로 비교군 평균에 수축시킨 승률 |
| `performance_score` | 성능 검증 축: 수축 승률의 z-점수 |
| `persistence_score` | 최근 주간 승률 흐름 EWMA (진단용, 점수에 직접 미반영) |
| `pick_stability_multiplier` | 레거시 산식 배율 (진단용, 점수에 직접 미반영) |
| `total_score` | 랭크 산정에 쓰는 메타 지배력 종합 점수 |
| `score_strength` | 특이 신호용 메타 유형 라벨 (메타 지배/과열 주의/밴 압박/저평가 픽/전문가 픽/비주류/보통) |
| `pick_rate_warning` | 저픽률 경고 라벨 |
| `rank` | S/A/B/C/D 랭크 |

### 퍼크 컬럼

| 컬럼 | 설명 |
|---|---|
| `hero`, `hero_slug`, `role`, `category` | 영웅 기본 정보 |
| `perk_type`, `perk_name`, `perk_description`, `pick_rate` | 퍼크 종류, 이름, 설명, 선택률 |
| `perk_slug`, `perk_image_url`, `perk_image_raw_url` | 퍼크 식별자와 이미지 URL |
| `hero_image_url`, `source_url`, `update_date` | 영웅 이미지, 출처 URL, 수집일 |

### 패치노트 JSON

- `patch_notes.json`: 패치 ID, 제목, 날짜, 공식 원문 URL, 원문/파싱 내용, 요약, 영향 영웅, 영웅 밸런스 패치 여부를 저장합니다.
- `patch_ai_analysis.json`: 패치별 분석일, 분석 모델, 분석 단계, 직접/간접 영향 영웅, 요약, 지표 스냅샷 정보를 저장합니다.

---

## 영웅 랭크 산정 방식

랭크는 "메타 지배력"을 측정합니다: 판에 얼마나 등장하는가(존재감)를 주축으로, 등장했을 때 실제로 이기는가(성능)로 검증하는 2축 구조입니다. 모든 z-점수는 `(data_tier, map, role)` 비교군 안에서 계산합니다.

```text
# 존재감 축 (가중 0.65): 픽률과 밴률의 합 = 드래프트에서 차지하는 지분
# 밴률이 높은 영웅은 픽이 강제로 눌리므로 둘을 합쳐 한 번에 측정
presence_score = z(log1p(pick_rate + β * ban_rate))    # β = PRESENCE_BAN_WEIGHT, 기본 1.0

# 성능 축 (가중 0.35): 픽률 가중 경험적 베이즈 수축 승률
# 실제 게임 수가 없으므로 픽률을 표본 크기 대리로 사용, k = 비교군 픽률 중앙값
shrunk_win_rate = (pick_rate * win_rate + k * 비교군평균승률) / (pick_rate + k)
performance_score = z(shrunk_win_rate)

total_score = 0.65 * presence_score + 0.35 * performance_score
```

`score_strength`는 매우 뚜렷한 메타 신호에만 붙이는 유형 라벨입니다. 일반 구간인 `보통`은 화면 배지로 표시하지 않습니다.

| 존재감 | 성능 | 라벨 | 의미 |
|---|---|---|---|
| 존재감 z ≥ 1.25 | 성능 z ≥ 0.75 | 메타 지배 | 픽/밴 존재감이 매우 크고 실제 성능도 좋음 |
| 픽률 z ≥ 1.25 | 성능 z ≤ -0.25 | 과열 주의 | 많이 픽되지만 승률 검증은 약함 |
| 밴률 z ≥ 1.5 | 픽률 z < 0 | 밴 압박 | 픽은 적지만 밴으로 강하게 의식됨 |
| 존재감 z < 0.5 | 성능 z ≥ 1.25 | 저평가 픽 | 덜 쓰이지만 수축 승률 기준 성능 신호가 매우 강함 |
| `pick_rate_z <= -1.0` | `win_rate_z >= 1.0` and 성능 z < 1.25 | 전문가 픽 | 낮은 픽률 대비 승률이 매우 좋은 숙련자형 후보 |
| 존재감 z ≤ -1.25 | 성능 z ≤ -0.25 | 비주류 | 존재감도 낮고 성능 신호도 약함 |
| 그 외 | 그 외 | 보통 | — |

랭크는 분위수로 강제 배분하지 않고 절대 점수 기준으로 산정합니다. 존재감 축은 하한이 눌린 분포(픽+밴은 음수가 될 수 없음)라 D 임계만 -1.00으로 보정했습니다.

```text
S: total_score >= 1.25
A: 0.50 <= total_score < 1.25
B: -0.50 < total_score < 0.50
C: -1.00 < total_score <= -0.50
D: total_score <= -1.00
```

비교군의 격차가 작으면 S나 D가 없을 수 있습니다. 실제 게임 수가 저장되지 않으므로 표본 크기 필터 대신 `pick_rate`가 1.0% 미만이면 저픽률 경고를 표시합니다.

### 밴률 합산에 대한 판단 근거

밴률에는 강함 외에 불쾌함, 티어별 대처 어려움, 유행이 섞여 있지만 합산 구조를 유지합니다.

- 그룹 내 밴률-승률 상관(0.26)이 픽률-승률 상관(0.25)과 동급이라, 밴률이 픽률보다 더 오염된 신호가 아닙니다.
- 티어별 대처 어려움은 비교군이 티어별로 분리되어 있어 해당 티어 리스트에만 반영되며, 이는 오차가 아니라 티어별 티어리스트가 담아야 할 정보입니다.
- 불쾌함 밴(고밴·평균이하 승률)은 실재하지만, 점수를 수정하는 대신 `과열 주의` 라벨과 진단 리포트의 `overheat_monitor`로 노출합니다.
- β를 1.0에서 0.5로 낮춰도 순위 상관 0.99, 상위 25% 집합 일치율 94%로 저위험 결정입니다. `overheat_monitor`가 지속적으로 기준(15%)을 넘으면 `PRESENCE_BAN_WEIGHT` 하향을 검토합니다.

---

## 랭크 진단 리포트

`python update.py --mode stats` 실행 시 `data/latest/rank_diagnostics.json`을 저장합니다. 이 파일은 메인 랭크 산식을 자동 변경하지 않고 안정성을 점검하는 보조 리포트입니다.

- `correlation_matrix`: 승률, 지속성, 존재감, 성능, 종합 점수 간 중복성 확인
- `overheat_monitor`: S/A 랭크 중 성능 z<0(존재감만으로 상위권) 비율. 지속적으로 15%를 넘으면 `PRESENCE_BAN_WEIGHT` 하향 검토
- `walk_forward`: 이번 주 점수가 다음 주 승률(`next_week_win_rate_z`)과 다음 주 존재감(`next_week_presence_z`)을 얼마나 설명하는지 후보 산식별 비교. 산식의 목표가 지배력이므로 존재감 목표가 1차 기준
- `sensitivity`: 존재감 가중치(0.55~0.75)와 밴 가중치 β(0.5~1.0)를 바꿨을 때 S/A/B/C/D 배정이 얼마나 흔들리는지 확인

---

## 자동화

### GitHub Actions

`main.yml`은 매일 00:00 UTC, 한국 시간 09:00에 `python update.py --mode all`을 실행하고 변경된 데이터를 커밋/푸시하는 워크플로 예시입니다.

GitHub Actions에서 사용하려면 일반적으로 다음 위치로 배치합니다.

```text
.github/workflows/main.yml
```

### 로컬 Ollama 패치 분석

macOS에서는 `scripts/run_local_ai_patch_update.sh`와 `scripts/com.da.overwatch.ai-patch.plist`로 매일 로컬 Ollama 패치 분석을 실행할 수 있습니다. 자세한 설치, 상태 확인, 재시작 방법은 `scripts/LOCAL_AI_PATCH_AUTOMATION.md`를 참고하세요.

---

## 실행 전 확인사항

- Selenium 수집을 위해 Chrome 또는 Chromium이 필요합니다.
- Parquet 파일을 읽고 쓰기 위해 `pyarrow`가 필요합니다.
- 패치 AI 분석을 사용하려면 Ollama 서버가 `OLLAMA_GENERATE_URL`에서 응답해야 합니다.
- 대시보드는 기본적으로 `data/latest/latest_tier.parquet`가 있어야 정상 동작합니다.
- `data/patch_notes/patch_notes.json` 등 데이터 파일은 수집 결과이므로, 수동 변경분이 있는 상태에서 자동화나 갱신 스크립트를 실행하면 변경 사항이 섞일 수 있습니다.

---

## 새 AI 에이전트를 위한 작업 가이드

1. 먼저 `git status --short`로 사용자의 기존 변경분을 확인하세요.
2. 대시보드 동작을 이해하려면 `main.py`, `app_data.py`, `ui.py`, `pages/*.py` 순서로 읽으세요.
3. 데이터 생성 로직을 바꿀 때는 `update.py`의 상수, 저장 경로, CLI 옵션, `STATS_COLUMNS`를 함께 확인하세요.
4. 데이터 파일을 직접 수정하기보다 가능하면 `python update.py --mode ...`로 재생성하세요.
5. 패치 AI 분석은 로컬 Ollama 상태와 환경변수에 따라 결과가 달라질 수 있습니다.
6. 이미 수정된 데이터 파일이 있으면 사용자가 만든 변경일 수 있으므로 덮어쓰기 전에 의도를 확인하세요.

---

## 향후 개선 아이디어

- `main.yml`을 `.github/workflows/main.yml`로 이동해 GitHub Actions 기본 구조에 맞추기
- 테스트 코드와 데이터 검증 파이프라인 추가
- 수집 실패, 빈 데이터, 스키마 변경을 검증하는 smoke test 추가
- 패치노트의 버프/너프 이력을 영웅별 라벨로 구조화해 랭크 산식 검증에 활용

---

## License

개인/학습 목적 예제 프로젝트입니다. 배포 시 Blizzard 및 외부 데이터 소스의 정책과 라이선스를 반드시 확인하세요.
