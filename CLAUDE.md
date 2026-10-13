# CLAUDE.md

오버워치 2 경쟁전 메타 대시보드 (Streamlit 멀티페이지). 데이터 수집·랭크 산식·환경변수는 `README.md`를 본다.
이 파일은 README에 없는 것 — 체크포인트, 실행·배포 주의점, UI 구조, 디자인·반응형 규칙, Streamlit 함정, 작업 기록 — 만 적는다.
`ow2_streamlit_refine_v2.md`는 과거 지시서(2026-08-17)다. 수치가 다르면 CLAUDE.md가 우선이다.

## 체크포인트

| 태그 | 상태 |
|---|---|
| `checkpoint-2026-09-30` | 디자인 전면 개편 + 모바일·태블릿 대응 완료. 사용자가 PC·폰·아이패드에서 확인하고 "완벽"하다고 한 상태 |

- 목록: `git tag -n`
- 지금과 비교: `git diff checkpoint-2026-09-30 -- main.py ui pages assets .streamlit`
- 그때 모습만 보기: `git switch --detach checkpoint-2026-09-30` → 로컬 실행 → `git switch main`
- **되돌리기(기본)** — UI 코드만 되돌리고 데이터는 최신으로 둔다:
  ```bash
  git restore --source=checkpoint-2026-09-30 --staged --worktree -- main.py ui pages assets .streamlit
  git commit -m "revert: UI 를 checkpoint-2026-09-30 으로" && git pull --rebase && git push
  ```
  복원 범위에 `app_data.py`·`requirements.txt`는 없다. 페이지가 `app_data`를 import하므로 커밋 전에 로컬에서 네 페이지가 뜨는지 본다.
  push 후 Streamlit Cloud에서 Reboot(아래 배포 참고).
- 파일 하나만: `git restore --source=checkpoint-2026-09-30 -- assets/style.css`
- **하지 말 것**: `git reset --hard <태그>` 후 강제 push. GitHub Actions가 매일 `data/`를 커밋하므로 태그 이후 데이터가 전부 사라진다.
- 태그 이후 일부러 바꾼 UI는 아래 작업 기록에 있다. 되돌린 뒤 다시 적용할지 확인한다.
- 새 체크포인트: `git tag -a checkpoint-YYYY-MM-DD -m "설명" && git push origin checkpoint-YYYY-MM-DD` 후 위 표에 한 줄 추가.

## 로컬 실행 · 배포

- `.venv/bin/streamlit` 런처는 옛 경로를 가리켜 깨져 있다. `.venv/bin/python -m streamlit run main.py`로 띄운다.
- 앱은 기본으로 GitHub raw에서 데이터를 읽는다(30분 TTL). 로컬 파일로 보려면 `OW2_LOCAL_DATA=1`.
- `assets/style.css`는 `st.cache_data`로 캐시되고 `.streamlit/config.toml`은 시작할 때만 읽는다. 둘 다 고치면 서버를 재시작해야 반영된다.
- 배포: Streamlit Community Cloud (https://ow2metatracker.streamlit.app). keep-alive 워크플로가 앱을 늘 깨워 둬서 push만으로는 코드가 바뀌지 않는다. push 후 대시보드에서 **Reboot**. 문서·스크립트만 바뀐 push는 Reboot이 필요 없다.
- GitHub Actions가 매일 09:00 KST에 `main`으로 `data/`를 커밋한다. push 전에 `git pull --rebase`.
- `git add -A`·`git add .` 금지. 루트에 추적하지 않는 참고 이미지(`2hEW9.jpg`, `Overwatch_logo_1024.png`)가 있다. 커밋할 파일을 지정한다.
- 테스트: `.venv/bin/python test_sample_size.py`(`update.py`의 표본 크기 보정), `.venv/bin/python test_map_heroes.py`(전장별 영웅 선정), `.venv/bin/python test_overheat.py`(랭크 진단의 과열 감시), `.venv/bin/python test_perks.py`(특전 수집 검증·키 빈칸 보정), `.venv/bin/python test_patch_impact.py`(밸런스 패치 전후 비교). `ok`가 나오면 통과.

## UI 구조

- `ui/` 패키지: `tokens`(팔레트) · `theme`(CSS 주입) · `layout`(`page_shell`, 컬럼 비율) · `components`(HTML 카드) · `filters`(전역 필터) · `badges`(랭크 타일·티어 아이콘) · `plotly_theme`.
- 모든 페이지는 `page_shell`로 시작한다: 페이지 머리 → 사이드바(메뉴·필터·고지) → 본문 메뉴·필터 줄 → 본문 → 하단 고지. 본문 메뉴 줄과 하단 고지는 사이드바가 접혔을 때만 보인다.
- 카드류는 위젯 조합이 아니라 HTML 한 덩어리(`st.markdown(..., unsafe_allow_html=True)`)다.
- 우측 레일 카드는 `*_html()`로 만들어 두 번 낸다: 우측 칸(`.rail-side`)과 좁을 때 표 위 스와이프 줄(`.rail-strip`).
- 영웅 상세는 메뉴에 없다. 카드의 `?hero=` 링크를 그 페이지(메인, 전장별 영웅)가 받아 `st.switch_page`로 넘긴다.
- 필터 정본은 `st.session_state["selected_tier" | "selected_role"]`. 사이드바 위젯과 본문 필터 사본(`render_inline_filters`)이 이것을 공유한다.

## 디자인 규칙

- 팔레트는 세 곳이 짝이다: `ui/tokens.py`, `assets/style.css`의 `:root`, `.streamlit/config.toml`. 한 곳만 고치면 어긋난다.
- 액센트는 오버워치 오렌지 `#f99e1a` 한 색. 예전 `#ff4655`는 발로란트 브랜드색이라 쓰지 않는다. 초록·파랑·빨강은 승률·픽률·밴률 의미로만 쓴다.
- 랭크 색 단일 출처는 `ui/badges.py`의 `RANK_COLORS`. A는 노랑(액센트와 붙어 보이지 않게).
- 폰트는 Pretendard 한 벌 + `tabular-nums`. Black Han Sans·Bebas는 AI 템플릿 인상이라 뺐다.
- 그림자는 HERO 카드에만. 나머지 카드는 1px 선 + 단색 면. 라운드 위계 16 / 12 / 6.
- 이모지 대신 인라인 SVG. 공식 오버워치 로고는 브랜드로 쓰지 않는다(비공식 사이트 고지가 있다).
- 모션은 마운트 때 한 번(`animation-fill-mode: backwards`)이고 `prefers-reduced-motion`이면 끈다.

## 반응형 규칙

- 기준은 창 폭이 아니라 영역 폭(container query)이다. 사이드바를 펼친 아이패드는 창이 820px이어도 본문은 500px이다.
  - `page`(본문) 780px 이하: 컬럼을 한 줄로 쌓고, 우측 레일은 표 위 스와이프 줄로
  - `page` 520px 이하: 본문 필터 줄·영웅 추이 필터를 한 줄 반반으로
  - `board`(순위표) 700px 이하: 5열 표 → 한 줄 요약 목록
  - `hero` 880 / 760 / 560, `rot` 620, `kpi` 460
  - 전장별 영웅 격자(`.mh-grid`)는 `auto-fill minmax(320px)`라 query 없이 영역 폭을 따른다(PC 3열, 아이패드 가로 2열, 폰 1열).
- 창 폭(`@media`)은 폰 전용 처리(640px, » 버튼 숨김)에만 쓴다. 예외로 `.patch-intel-top` 줄바꿈(860px)이 창 폭 기준으로 남아 있다. 새 레이아웃 규칙은 container query로 쓴다.
- 카드·표 행의 hover 효과는 `@media (hover: hover)` 안에 있고, 새로 넣는 hover도 거기에 둔다. 그 밖의 `:hover`(사이드바 링크, Streamlit 위젯, 영웅·패치 링크, TOP 4 순환 정지)는 블록 밖에 있다.
- 터치는 `:active` 눌림 피드백을 쓰고, TOP 4는 터치에서 자동 순환 대신 스와이프다.
- 사이드바 펼침 여부는 `[data-testid="stSidebar"][aria-expanded]`로 판단한다.

## Streamlit 함정 (한 번씩 밟은 것)

- 사이드바 폭 고정은 `[aria-expanded="true"]`에만 건다. 전체에 `min-width`를 걸면 접어도 256px 자리를 차지한다(min이 Streamlit의 `max-width: 0`을 이긴다).
- 마크다운 컨테이너의 `margin-bottom: -1rem`이 HTML 블록 사이 간격을 먹는다. style.css에 되돌리는 규칙이 있다.
- 투명 헤더가 화면 위 60px 탭을 가로챈다. 버튼만 `pointer-events`를 받게 했다.
- `st.markdown` 링크(`?hero=`)는 전체 리로드라 세션이 새로 뜬다. `filter_qs()`로 tier·role을 URL에 붙인다.
- 상태를 바꾸는 조작(정렬 등)은 링크가 아니라 위젯으로 만든다. 순위표 정렬이 `?sort=` 링크였을 때는 누를 때마다 세션이 새로 떠서 스크롤이 맨 위로 가고 "다시 누르면 반대 방향"이 동작하지 않았다. 지금은 표 위 `st.pills`이고, 켜진 칩을 다시 누르면 값이 `None`이 되는 것을 방향 뒤집기로 쓴다.
- 일괄 폰트 규칙이 아이콘 폰트를 덮는다. 위젯 라벨의 `:material/...:` 아이콘은 testid 없이 `span[role="img"]`로 나와서 style.css에서 따로 되돌린다.
- 한 `st.markdown`에서 연 div를 다른 `st.markdown`에서 닫을 수 없다(빈 div가 된다).
- HTML 조각 사이 빈 줄·들여쓰기는 코드 블록으로 파싱된다. `_one_line()`을 쓴다.
- 마크다운 안 `<img>`에는 Streamlit이 `object-fit: scale-down`을 건다. `cover`로 채우려면 `!important`가 필요하다.
- `icon_selectbox`는 옆에 `<style>` 마크다운을 하나 더 낸다. 가로 컨테이너에서는 그 칸을 숨긴다.
- `data-testid` 셀렉터에 기대므로 streamlit은 1.50.0으로 고정. 올리면 셀렉터부터 확인한다.
- 로컬 파이썬은 3.9라 f-string 안에 같은 따옴표를 중첩할 수 없다.
- Plotly 2D·추이 차트는 `dragmode=False`(폰에서 스와이프를 확대가 먹었다).
- 3D 차트는 `scene.dragmode="turntable"`을 명시한다. 점 선택 모드(`on_select`)에서 Streamlit이 `layout.dragmode`를 `pan`으로 두고 scene이 그걸 물려받아, 드래그가 회전이 아니라 이동이 되어 큐브가 화면 밖으로 나갔다. 휠 확대는 끄고(`scrollZoom: False`) 모드바에는 시점 초기화 버튼만 둔다. 3D 캔버스 위 스와이프는 회전이라 페이지가 스크롤되지 않는다.
- 3D 카메라를 잴 때는 `_fullLayout.scene._scene.getCamera()`를 읽는다. `_fullLayout.scene.camera`는 드래그 중에 갱신되지 않아 "회전하지 않는다"로 잘못 읽힌다.

## 검증

UI를 고치면 폰 390×844(터치), 아이패드 820×1180 사이드바 펼침·접힘, 1180×820, PC 1440×900에서 본다.
`scripts/ui_check.py`가 헤드리스 Chrome으로 요소 위치·가로 넘침·터치 동작을 잰다. `websocket-client`가 필요한데 앱 의존성이 아니라 `requirements.txt`에 없다(새 venv면 `.venv/bin/pip install websocket-client`). 서버를 띄운 뒤 다른 셸에서 돌린다:

```bash
OW2_LOCAL_DATA=1 .venv/bin/python -m streamlit run main.py --server.port 8599 --server.headless true
.venv/bin/python scripts/ui_check.py                      # layout · sidebar · interact 전부
.venv/bin/python scripts/ui_check.py layout --page main   # 일부만
```

수치는 표준 출력으로, 스크린샷은 `logs/ui_check/`(gitignore)에 남는다. 가로 넘침이나 검사 예외가 있으면 종료 코드 1.

## 작업 기록

결정과 근거는 README에 있다. 여기에는 무엇을 했는지와 README에 없는 유지보수 메모만 둔다.

### 2026-10-02 랭크 산식 외부 리뷰 반영 (c3ea612, 15c14f5, 141a1e3)

- 메인 "랭크는 어떻게 산정되나요?"·"메타 유형 라벨은 뭔가요?" 확장 패널을 다시 썼다: 메타 지배력 순위라는 첫 줄, 등급 구간 표기, 라벨 기준과 우선순위, 수축 설명, 넥슨 누적 집계 문구.
- 과열 감시(`build_overheat_monitor`): 고정 기준 15%를 "비교군 안에서 성능을 1000번 섞은 기준선"과의 비교로 바꿨다. `test_overheat.py`를 추가했다.
- 존재감 가중치와 수축 방식 변경안을 검토하고 보류했다. 결정과 근거는 README "밴률 합산에 대한 판단 근거"·"수축 방식에 대한 판단 근거".
- 유지보수 메모:
  - 산식 상수(가중치·랭크 구간·라벨 기준)는 `update.py`와 `app_data.py`에 따로 있다. 대시보드는 데이터를 불러올 때 `app_data.py` 값으로 점수를 다시 계산하므로 한쪽만 고치면 진단 리포트와 화면이 어긋난다. 가중치 두 개는 환경변수라 Actions와 Streamlit Cloud Secrets 양쪽에 넣는다.
  - 확장 패널 문구는 README "영웅 랭크 산정 방식"과 짝이다. 산식·임계값을 바꾸면 `main.py` 확장 패널도 같이 고친다.
  - 확장 패널의 "지금 집계는 9월 9일 패치부터"는 넥슨이 누적 집계를 초기화하면(새 시즌·큰 패치) 날짜를 고친다.
  - 진단 리포트의 `s_membership_change_rate`는 분모가 전체 행이라 S 구성 변화(실제 약 20%)가 3%처럼 작게 보인다. 아직 고치지 않았다. 이 값을 근거로 "랭크가 안정적"이라고 말하지 않는다.
  - 과열 수치의 기준선은 2026-10-01 데이터로 다시 계산한 실제 19.3% · 섞기 31.2% · 경고선 29.9%이고, 7/21 이후 경고는 0번이었다. README의 19.0%는 9/30 값이다. 커밋된 10/01 `rank_diagnostics.json`은 바꾸기 전 형식이라 섞기 기준선이 없다.

### 2026-10-12 메인 "승률 높은 전장" 카드 삭제

- 종합 1위 HERO 카드와 TOP 4 사이에 있던 1위 영웅의 전장 카드 4장을 지웠다. 1위 한 명에 대한 내용이 다른 영웅 TOP 4에 끊겨 어색했고, 같은 내용이 영웅 상세 "전장별 승률"에 있다.
- 메인 흐름은 HERO(1명) → TOP 4 → 전체 순위(53명)다. `render_map_cards`·`.map-*` CSS·`ui_check.py`의 `maps` 측정도 같이 지웠다.
- `checkpoint-2026-09-30`으로 되돌리면 이 카드가 돌아온다.

### 2026-10-12 특전 출처를 owperks에서 블리자드 공식(OverFast 경유)으로

- owperks의 특전 %는 게임 픽률이 아니라 그 사이트 방문자 투표였고, owperks 약관이 재배포를 금지한다. 출처 표시도 없이 게임 픽률처럼 보이고 있었다.
- 특전 이름·설명·아이콘은 OverFast `/heroes/{key}?locale=ko-kr`에서 받는다(블리자드 영웅 페이지 내용). 바꾸기 전 owperks 데이터와 이름·설명이 모두 같았다. %는 공식 출처가 없어 뺐다.
- 영웅 상세 특전 카드는 %·막대·툴팁을 없애고 설명을 카드에 바로 보인다. 툴팁용 `:has` 쌓임 순서 규칙과 900px 미디어쿼리도 지웠다.
- `update.py`에서 Selenium을 쓰던 곳이 특전 수집 하나뿐이라 `requirements.txt`의 `selenium`·`webdriver-manager`, 데이터 갱신 워크플로의 webdriver 캐시 단계, `DRIVER_*` 환경변수를 지웠다. keep-alive 워크플로는 selenium을 따로 설치해 쓰므로 영향이 없다.
- 사이드바 고지의 "Overwatch Wiki (CC BY-NC-SA)"를 고쳤다. 위키의 CC 라이선스는 글에만 붙고 영웅 렌더 파일은 블리자드 저작물로 분류된다.
- 유지보수 메모:
  - 수집은 통계 영웅이 하나라도 빠지거나 특전이 2+2가 아니면 저장하지 않는다. 화면에 특전이 안 바뀌면 Actions 로그의 "특전 수집 실패"를 본다. `role_dict`에 아직 없는 새 영웅도 OverFast 이름으로 수집된다(넥슨 통계에 새 영웅이 먼저 들어온다. 2026-10-12 독트린).
  - 키 그림 빈칸(`PERK_KEY_FIXES`)은 손으로 채우는 표다. 로그에 "키 그림 빈칸" 경고가 보이면 블리자드 영웅 페이지에서 그림이 왼쪽/오른쪽 버튼인지 보고 한 줄 추가한다.

### 2026-10-12 패치노트 전문 게시 중단

- 메인 "최근 패치노트"의 "패치노트 자세히 보기"가 블리자드 패치노트 전문(약 2만 자)을 그대로 보이고 있었다. "패치노트 핵심 요약"(요약 최대 8줄 + 공식 원문 링크)으로 바꿨다.
- `patch_notes.json`에 전문(`raw_content`·`parsed_content`)을 저장하지 않는다(`update.py`의 `strip_patch_fulltext`). 기존 16개 행에서도 지웠다(335KB → 31KB). 과거 커밋에는 남아 있지만 매일 데이터 커밋이 쌓이는 저장소라 기록을 다시 쓰지 않는다.
- AI 패치 분석은 `upsert_patch_note`가 돌려주는 전문 있는 행(같은 실행에서 받은 본문)을 쓰므로 영향이 없다. 로컬 Ollama 자동화도 매번 새로 받는다.
- 같은 날 특전 수집이 `role_dict`에 없는 새 영웅(독트린)을 건너뛰던 회귀를 고쳤다. 오후 데이터 갱신에서 넥슨 통계에 독트린이 들어와 상세 페이지 특전이 비어 있었다.

### 2026-10-12 솜브라 지원 재편 반영

- 넥슨 통계는 2026-10-07 데이터부터 솜브라를 지원으로 준다. 순위·포지션 필터·비교군(z-점수)은 그날 행의 역할을 쓰므로 자동으로 반영됐다.
- 손으로 들고 있던 표는 옛 분류였다: `update.py`의 `role_dict`(공격 → 지원, 독트린도 추가), `app_data.py`의 `HERO_SUBROLES`(수색가 → 전술가). 특전 파일의 `role` 열은 읽는 곳이 없어 뺐다.
- 영웅 추이의 역할 필터가 행마다 역할로 걸러서, 지원에서는 10/7 이후만, 공격에서는 그 전만 보였다. 지금 역할로 영웅을 고르고 추이는 전체 기록을 보이게 고쳤다. 역할이 바뀐 영웅은 차트 위에 "그 전 랭크·종합 점수는 다른 비교군 값"이라는 안내가 뜬다. 공격 필터에서는 솜브라의 공격 시절 기록을 볼 수 없다(전체 포지션에서 본다).
- 날짜를 넘어 (영웅, 역할)로 묶는 곳은 역할이 바뀐 날 전후가 이어지지 않는다: 진단 리포트의 지속성(`build_recent_persistence_frame`)·walk-forward, 메인 "최근 변동"(`load_score_deltas`, 비교 기준일이 10/7 이전이면 지원 z와 공격 z를 뺀다). 지속성은 진단용이고 최근 변동의 기준일은 지금 10/11이라 화면에는 영향이 없다.
- 같은 날 독트린 등록에서 `HERO_SUBROLES`를 없앴다(아래). 역할·하위 역할은 이제 손으로 고치지 않는다.

### 2026-10-12 독트린 등록 + 영웅 정보를 OverFast 목록에서

- 특전 수집이 받는 OverFast `/heroes?locale=ko-kr`를 `data/latest/heroes.json`(한글 이름·key·역할·하위 역할·초상화)으로 저장한다. 특전 검증을 통과했을 때만 바뀐다.
- `app_data.py`의 손 표 `HERO_NAME_TO_API_NAME`·`HERO_PORTRAIT_FALLBACKS`·`HERO_SUBROLES`와 앱이 매번 OverFast를 부르던 초상화 조회를 지웠다. 초상화·하위 역할은 `heroes.json`에서, 배너 아트·영웅색은 그 key로 찾는다. 바꾸기 전후로 기존 53명의 초상화 URL·배너·영웅색·하위 역할이 모두 같았다.
- 독트린 배너는 공식 스플래시만 쓴다(영웅색도 스플래시에서 뽑았다). 같은 날 모든 영웅을 스플래시로 통일했다(아래). 다른 영웅처럼 위키 전신 렌더를 쓰려면 위키 이미지 서버에 Referer를 위키로 꾸며 보내야 해서(핫링크 차단 우회) 하지 않았다. 블리자드 공식 페이지의 렌더(`*_Beauty_Individual_*.png`)는 배경이 있는 장면이라 컷아웃으로 쓸 수 없다.
- 새 영웅 등록 순서(유지보수 메모):
  1. `update.py`의 `role_dict`에 넣는다. OverFast 이름을 통계 표기로 맞추는 `normalize_hero_name`이 이 표에 없는 이름을 비슷한 기존 영웅으로 잘못 붙이지 않게 한다. 패치노트 표기가 통계와 다르면(D.Va/D.VA) `HERO_NAME_ALIASES`에도 넣는다. 특전·초상화·하위 역할은 넣지 않아도 다음 수집부터 나온다.
  2. 배너·영웅색: `.venv/bin/python scripts/fetch_hero_art.py <OverFast key>`. 매니페스트에 스플래시 주소·`focal_x`를 넣고, `hero_colors.json`에 색이 없으면 한 줄 추가한다.

### 2026-10-12 배너 아트를 공식 스플래시로 통일

- 메인 종합 1위 카드·영웅 상세 상단 카드·영웅 추이 세로 카드가 위키 전신 렌더 컷아웃 대신 독트린처럼 블리자드 공식 스플래시를 카드 배경으로 쓴다(TOP 4 카드는 원래 스플래시). 사용자가 독트린 카드가 더 자연스럽다고 해서 통일했다.
- `get_hero_banner_art`는 `{splash_url, focal_x}`만 돌려준다. 컷아웃 `<img>` 분기, `.hero-showcase-art`·림라이트 CSS, `ui_check.py`의 글자·아트 겹침 측정을 지웠다.
- 블리자드 그림을 고친 복사본을 공개 저장소에 두지 않도록 `static/hero_art/` 53장(6MB)을 지웠다. 과거 커밋에는 남아 있다(기록을 다시 쓰지 않는다).
- `fetch_hero_art.py`는 위키 렌더·밝기 보정을 빼고 매니페스트(스플래시 주소·`focal_x`)와 빠진 영웅색만 만든다. `extract_hero_colors.py`는 합쳐서 지웠다. 매니페스트의 `art_source`·`cutout_*`·`luma`·`use_cutout`도 지웠다. 새 스크립트로 독트린을 다시 돌려 `focal_x`·색이 그대로 나오는 것을 확인했다.
- 54명 스플래시를 같은 잘림 계산으로 모아 봤고, 인물이 가운데에 가까운 라이프위버·일리아리·한조도 PC·폰에서 숫자와 겹치지 않았다.

### 2026-10-13 AI 패치 분석 → 밸런스 패치 전후 지표 + 기본 티어 전체

- 로컬 Ollama(qwen3:14b) 패치 분석을 지웠다. 맥의 launchd가 매일 돌려 맥에서 직접 push하는 구조였는데, 7/12에 작업 폴더 변경으로 `git pull --rebase`가 실패한 뒤 멈췄고 LaunchAgent도 등록이 풀려 있었다. 저장된 분석 4개 중 3개는 LLM이 아니라 문장 틀이었고, 입력도 골드 티어의 "어제 대비" 변화라 넥슨이 며칠씩 같은 값을 주는 동안 패치 효과를 못 잡았다. 메인에는 3개월째 "아직 AI 분석이 생성되지 않았습니다"가 떠 있었다.
- 대신 메인 "최근 패치노트"와 영웅 상세에 "밸런스 패치 전후"를 둔다. 직접 변경 영웅의 패치 직전 일별 스냅샷 → 지금을 선택한 티어 기준으로 비교한다(`app_data.patch_impact`, 따로 저장하지 않는다). 메인은 승률·픽률·밴률 변화 합이 큰 5명 + 나머지 펼치기, 상세는 그 영웅이 직접 변경 대상일 때만.
  - 넥슨 수치는 평일마다 조금씩(하루 최대 0.4~2.5%p) 움직이고, 핫픽스(9/17 D.Mon)에는 집계가 새로 시작되지 않는다. 그래서 "수치가 직전과 같은가"가 아니라 "패치 뒤 7일 안에 새 집계가 있었나"(`find_aggregate_reset`, 전체 티어 변화 중간값 0.5%p)로 판단한다. 기준은 10/09 한 번의 새 집계로 정했으니, 다음 시즌 초기화 날 중간값을 확인한다.
  - 정렬에 종합 점수 차이를 쓰지 않는다. 역할이 바뀐 영웅은 다른 비교군의 z-점수끼리 빼게 된다.
  - 메인의 `?hero=` 처리는 포지션·검색으로 거른 표가 아니라 전체 데이터에서 영웅을 찾는다. 패치 카드는 다른 포지션 영웅으로도 링크한다.
  - `load_daily_history`는 넥슨 출처 이전 달(6~8월, 한 달 약 23MB) 파일을 받지 않고 전체 전장 행·필요한 열만 남긴다.
- 지운 것: `update.py`의 Ollama·지표 요약·문장 다듬기·fallback(약 580줄), 통계 갱신 결과 반환, `scripts/run_local_ai_patch_update.sh`·`com.da.overwatch.ai-patch.plist`·`LOCAL_AI_PATCH_AUTOMATION.md`, `data/patch_notes/patch_ai_analysis.json`, `.gitignore`의 `data/local_run_state/`. 패치노트 행은 이제 전문을 아예 만들지 않는다. `strip_patch_fulltext`는 예전 파일이 복원될 때를 대비해 저장 직전에 남겨 둔다.
- 패치노트 영향 영웅을 통계 표기로 맞췄다(D.Va → D.VA, D.Mon → D.MON). 기존 7개 행의 영웅 목록과 요약 문장도 고쳤다. 화면이 영웅 행과 이름으로 바로 잇는다.
- 일별 스냅샷 읽기를 `load_daily_history`로 묶어 "최근 변동"(`load_score_deltas`)과 같이 쓴다.
- 첫 화면 티어 기본값을 골드에서 전체 티어로 바꿨다(`ui/filters.py`의 `FILTER_DEFAULTS`). 골드 기본은 첫 커밋(2026-04-13)부터 근거 없이 있던 값이다. 2026-10-12 데이터로 전체 티어와 골드는 랭크 47/54명이 같고 순위 상관 0.99였다(전체 티어는 대부분 골드·플래티넘 경기).
- 맥에 남은 것: Ollama와 모델(9GB), `logs/local_ai_patch_update.log`·`launchd_ai_patch.*.log`(gitignore). 앱은 더 이상 쓰지 않는다.
