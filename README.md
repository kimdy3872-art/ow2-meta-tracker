# Overwatch 2 경쟁전 메타 분석 대시보드

오버워치 2 경쟁전 데이터를 수집·분석하고, 티어별/포지션별 승률·픽률·밴률 기반의 영웅 랭크를 Streamlit으로 시각화하는 프로젝트입니다.

---

## 주요 기능

| 페이지 | 설명 |
|---|---|
| **메인** | 티어·포지션·영웅 필터, 승률/픽률/밴률 기반 S/A/B/C/D 랭크 테이블, 장인챔프 표시 |
| **픽률/승률 분포** | 선택 티어·포지션 기준 분포 시각화 |
| **영웅 시계열** | 영웅별 승률·픽률·밴률 변화 추이 확인 |
| **영웅 상세** | 특정 영웅의 세부 지표 및 퍼크 정보 확인 |

---

## 기술 스택

| 분류 | 라이브러리 |
|---|---|
| 대시보드 | Streamlit |
| 데이터 처리 | Pandas, NumPy |
| 시각화 | Plotly |
| 크롤링 | Selenium |

---

## 프로젝트 구조

```
Overwatch_analysis/
├── main.py                         # 메인 대시보드
├── update.py                       # 경쟁전/퍼크 통합 수집
├── update_perk.py                  # (호환용) update.py 래퍼
├── requirements.txt
├── data/
│   ├── latest/latest_tier.parquet   # (대시보드) 최신 Parquet
│   ├── latest/latest_perks.parquet   # (대시보드) 최신 퍼크 Parquet
│   └── history/weekly/year=YYYY/week=WW/tier_snapshot.parquet  # 주간 스냅샷
└── pages/
    ├── 1_pick_win_distribution.py
    ├── 2_hero_trends.py
    └── 3_hero_detail.py
```

---

## 시작하기

### 1. 저장소 클론

```bash
git clone <YOUR_REPOSITORY_URL>
cd Overwatch_analysis
```

### 2. 가상환경 생성 및 활성화

**macOS / Linux**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows (PowerShell)**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. 패키지 설치

```bash
pip install -r requirements.txt
```

### 4. 대시보드 실행

```bash
streamlit run main.py
```

브라우저에서 `http://localhost:8501` 로 접속합니다.

---

## 데이터 갱신

### 경쟁전 통계

```bash
python update.py
```

Blizzard 경쟁전 통계를 수집해 `data/latest/latest_tier.parquet`를 갱신합니다.  
동일 날짜 재수집 시 중복을 제거하고 최신 값을 유지합니다.
최신 데이터는 Parquet(`data/latest/latest_tier.parquet`)로 저장됩니다.
주간(월요일)마다 `data/history/weekly/year=YYYY/week=WW/tier_snapshot.parquet`에 스냅샷이 누적됩니다.
수집기는 Blizzard 응답에 맞춰 `rq=2`와 `rq=1`을 자동 후보로 시도하며, 정상 렌더링과 검증을 통과한 값을 채택합니다.

### 영웅 퍼크

```bash
python update.py --mode perks

# 옵션 예시
python update.py --mode perks --max-heroes 5
python update.py --mode perks --locale ko
```

OW Perks 데이터를 수집해 `data/latest/latest_perks.parquet`를 갱신합니다.

### 통합 실행 (권장)

```bash
python update.py --mode all
```

경쟁전 통계와 퍼크 데이터를 한 번에 갱신합니다.

---

## 데이터 컬럼 및 저장 구조


### 주요 저장 파일

- **최신 Parquet**: `data/latest/latest_tier.parquet`
- **최신 퍼크 Parquet**: `data/latest/latest_perks.parquet`
- **주간 스냅샷**: `data/history/weekly/year=YYYY/week=WW/tier_snapshot.parquet`

### 경쟁전 통계 컬럼

| 컬럼 | 설명 |
|---|---|
| hero, role, data_tier | 영웅, 역할, 티어 |
| map, map_name, update_date | 맵 정보, 수집일 |
| win_rate, pick_rate, ban_rate | 승률, 픽률, 밴률 |
| win_rate_z, pick_rate_log, pick_rate_z, ban_rate_log, ban_rate_z | 정규화 지표 |
| persistence_score, pick_stability_multiplier, performance_score | EWMA 지속성, 픽률 안정성 보정, 성능 점수 |
| total_score, score_strength, pick_rate_warning, rank | 종합 점수, 절대 점수 강도, 저픽률 경고, 랭크 |


### 영웅 랭크 산정 공식

랭크는 "메타에서 성능이 좋은 영웅"을 찾기 위해 지표별 역할을 분리해 계산합니다.
승률은 성능의 핵심 지표, 최근 주간 승률 흐름은 EWMA 지속성, 픽률은 안정성 보정, 밴률은 약한 메타 압박 신호로 사용합니다.

```
base_score = 0.75 * z(win_rate)
           + 0.25 * persistence_score

pick_stability_multiplier = clip(1 + 0.08 * z(log(1 + pick_rate)), 0.85, 1.05)

total_score = base_score * pick_stability_multiplier
            + 0.05 * z(log(1 + ban_rate))
```

랭크는 분위수로 강제 배분하지 않고 절대 점수 기준으로 산정합니다.

```
S: total_score >= 1.25
A: 0.50 <= total_score < 1.25
B: -0.50 < total_score < 0.50
C: -1.25 < total_score <= -0.50
D: total_score <= -1.25
```

따라서 비교군이 평평하면 S나 D가 없을 수 있고, 정말 강하거나 약한 영웅만 양끝 랭크로 분리됩니다. `score_strength`에는 절대 점수 구간(압도적/강함/우세/보통/약세)을 함께 저장합니다.
실제 게임 수가 없으므로 표본 크기 필터 대신 `pick_rate`가 1.0% 미만이면 저픽률 경고를 표시합니다.

### 랭크 진단 리포트

업데이트 시 `data/latest/rank_diagnostics.json`에 랭크 산식 진단 결과를 저장합니다.
이 리포트는 메인 가중치를 자동 변경하지 않고, 현재 산식의 안정성을 점검하는 용도입니다.

- `correlation_matrix`: 승률, 지속성, 픽률, 밴률, 종합 점수 간 중복성 확인
- `walk_forward`: 이번 주 점수가 다음 주 승률 성과를 얼마나 설명하는지 후보 산식별 비교
- `sensitivity`: 가중치를 일부 흔들었을 때 S/A/B/C/D 배정이 얼마나 바뀌는지 확인

장기적으로는 패치 노트의 버프/너프 이력을 영웅별 라벨로 구조화해, 패치 이력 기반 회귀/분류 모델로 산식을 검증할 계획입니다.

### `data/latest/latest_perks.parquet`

| 컬럼 | 설명 |
|---|---|
| hero, hero_slug, role, category | 영웅 기본 정보 |
| perk_type, perk_name, perk_description, pick_rate | 퍼크 정보 및 상세 설명 |
| perk_slug, perk_image_url, perk_image_raw_url | 퍼크 이미지 |
| hero_image_url, source_url, update_date | 출처 및 수집일 |

---

## 참고 및 자동화

- Selenium 크롤링을 위해 **Chrome 또는 Chromium** 실행 환경이 필요합니다.
- 대시보드는 최신 Parquet(`data/latest/latest_tier.parquet`, `data/latest/latest_perks.parquet`) 기준으로 시각화합니다.

### 자동화 워크플로

GitHub Actions 등에서 `python update.py --mode all`을 매일 실행하면 최신/주간 데이터가 자동 적재됩니다.
주간 스냅샷은 월요일(요일 변경 가능)에만 생성됩니다.


## 향후 개선 아이디어

- GitHub Actions를 이용한 정기 데이터 수집 자동화
- 테스트 코드 및 데이터 검증 파이프라인 추가
- 시계열 변화(일자별 메타 변화) 페이지 추가

## License

개인/학습 목적 예제 프로젝트입니다.  
배포 시 사용 데이터 소스의 정책과 라이선스를 반드시 확인하세요.
