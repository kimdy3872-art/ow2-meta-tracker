# CLAUDE.md

오버워치 2 경쟁전 메타 대시보드 (Streamlit 멀티페이지). 데이터 수집·랭크 산식·환경변수는 `README.md`를 본다.
이 파일은 README에 없는 것 — 체크포인트, 실행·배포 주의점, UI 구조, 디자인·반응형 규칙, Streamlit 함정 — 만 적는다.
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
- 새 체크포인트: `git tag -a checkpoint-YYYY-MM-DD -m "설명" && git push origin checkpoint-YYYY-MM-DD` 후 위 표에 한 줄 추가.

## 로컬 실행 · 배포

- `.venv/bin/streamlit` 런처는 옛 경로를 가리켜 깨져 있다. `.venv/bin/python -m streamlit run main.py`로 띄운다.
- 앱은 기본으로 GitHub raw에서 데이터를 읽는다(30분 TTL). 로컬 파일로 보려면 `OW2_LOCAL_DATA=1`.
- `assets/style.css`는 `st.cache_data`로 캐시되고 `.streamlit/config.toml`은 시작할 때만 읽는다. 둘 다 고치면 서버를 재시작해야 반영된다.
- 배포: Streamlit Community Cloud (https://ow2metatracker.streamlit.app). keep-alive 워크플로가 앱을 늘 깨워 둬서 push만으로는 코드가 바뀌지 않는다. push 후 대시보드에서 **Reboot**. 문서·스크립트만 바뀐 push는 Reboot이 필요 없다.
- GitHub Actions가 매일 09:00 KST에 `main`으로 `data/`를 커밋한다. push 전에 `git pull --rebase`.
- `git add -A`·`git add .` 금지. 루트에 추적하지 않는 참고 이미지(`2hEW9.jpg`, `Overwatch_logo_1024.png`)가 있다. 커밋할 파일을 지정한다.
- 테스트: `.venv/bin/python test_sample_size.py`(`update.py`의 표본 크기 보정), `.venv/bin/python test_map_heroes.py`(전장별 영웅 선정), `.venv/bin/python test_overheat.py`(랭크 진단의 과열 감시). `ok`가 나오면 통과.

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
  - `hero` 880 / 760 / 560, `rot`·`maps` 620, `kpi` 460
  - 전장별 영웅 격자(`.mh-grid`)는 `auto-fill minmax(320px)`라 query 없이 영역 폭을 따른다(PC 3열, 아이패드 가로 2열, 폰 1열).
- 창 폭(`@media`)은 툴팁 위치(900px), 폰 전용 처리(640px, » 버튼 숨김)에만 쓴다. 예외로 `.patch-intel-top` 줄바꿈(860px)이 창 폭 기준으로 남아 있다. 새 레이아웃 규칙은 container query로 쓴다.
- 카드·표 행의 hover 효과는 `@media (hover: hover)` 안에 있고, 새로 넣는 hover도 거기에 둔다. 그 밖의 `:hover`(사이드바 링크, Streamlit 위젯, 영웅·패치 링크, 퍼크 카드·툴팁, TOP 4 순환 정지)는 블록 밖에 있다.
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
`scripts/ui_check.py`가 헤드리스 Chrome으로 요소 위치·가로 넘침·터치 동작을 잰다. 서버를 띄운 뒤 다른 셸에서 돌린다:

```bash
OW2_LOCAL_DATA=1 .venv/bin/python -m streamlit run main.py --server.port 8599 --server.headless true
.venv/bin/python scripts/ui_check.py                      # layout · sidebar · interact 전부
.venv/bin/python scripts/ui_check.py layout --page main   # 일부만
```

수치는 표준 출력으로, 스크린샷은 `logs/ui_check/`(gitignore)에 남는다. 가로 넘침이나 검사 예외가 있으면 종료 코드 1.
