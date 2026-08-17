"""Plotly 공통 테마.

pio.templates 에 "ow2" 를 등록하고 기본값으로 걸어서, 페이지에서 fig 를 만들면 배경·폰트·
축 색이 자동으로 붙게 한다. 페이지별 개별 스타일 코드는 두지 않는다.
style_chart() 는 제목·높이처럼 차트마다 다른 것만 얹는다.
"""

from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio

from .tokens import (
    GLOBAL_ACCENT_COLOR,
    GLOBAL_CHART_AXIS_COLOR,
    GLOBAL_CHART_GRID_COLOR,
    GLOBAL_CHART_PLOT_BG,
    GLOBAL_CHART_ZERO_COLOR,
    GLOBAL_DISPLAY_FONT_FAMILY,
    GLOBAL_FONT_FAMILY,
    GLOBAL_MUTED_TEXT_COLOR,
    GLOBAL_TEXT_COLOR,
)


def _axis_theme(**overrides):
    axis = dict(
        gridcolor=GLOBAL_CHART_GRID_COLOR,
        zerolinecolor=GLOBAL_CHART_ZERO_COLOR,
        linecolor=GLOBAL_CHART_AXIS_COLOR,
        tickcolor=GLOBAL_CHART_AXIS_COLOR,
        tickfont=dict(family=GLOBAL_DISPLAY_FONT_FAMILY, size=12,
                      color=GLOBAL_MUTED_TEXT_COLOR),
        title=dict(font=dict(family=GLOBAL_FONT_FAMILY, size=12,
                             color=GLOBAL_MUTED_TEXT_COLOR)),
    )
    axis.update(overrides)
    return axis


def style_chart(fig, title: str = "", height: int | None = None, scene: bool = False):
    """모든 Plotly 차트에 같은 테마를 입힌다.

    페이지마다 배경·그리드 색을 따로 적으면 팔레트를 바꿀 때마다 어긋나므로 여기로 모은다.
    scene=True 는 3D(scatter_3d)용. 3D 는 xaxis/yaxis 대신 scene 하위에 축이 있다.
    """
    layout = dict(
        font=dict(family=GLOBAL_FONT_FAMILY, size=13, color=GLOBAL_TEXT_COLOR),
        # 앱 프레임의 그라데이션이 비쳐 보이도록 종이 배경은 칠하지 않는다.
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=10, r=10, t=44 if title else 12, b=10),
        legend=dict(
            bgcolor="rgba(18, 20, 33, 0.82)",
            bordercolor="rgba(148, 150, 190, 0.22)",
            borderwidth=1,
            font=dict(family=GLOBAL_FONT_FAMILY, size=12, color=GLOBAL_TEXT_COLOR),
        ),
        hoverlabel=dict(
            bgcolor="#161a2b",
            bordercolor=GLOBAL_ACCENT_COLOR,
            font=dict(family=GLOBAL_FONT_FAMILY, size=12, color=GLOBAL_TEXT_COLOR),
        ),
    )
    if title:
        layout["title"] = dict(
            text=title,
            font=dict(family=GLOBAL_DISPLAY_FONT_FAMILY, size=19, color=GLOBAL_TEXT_COLOR),
            x=0,
            xanchor="left",
        )
    if height:
        layout["height"] = height

    if scene:
        layout["scene"] = dict(
            xaxis=_axis_theme(backgroundcolor="rgba(0,0,0,0)", showbackground=True),
            yaxis=_axis_theme(backgroundcolor="rgba(0,0,0,0)", showbackground=True),
            zaxis=_axis_theme(backgroundcolor="rgba(0,0,0,0)", showbackground=True),
        )
    else:
        layout["plot_bgcolor"] = GLOBAL_CHART_PLOT_BG
        layout["xaxis"] = _axis_theme(showline=True)
        layout["yaxis"] = _axis_theme(showline=True)

    fig.update_layout(**layout)
    return fig


def _register_template() -> None:
    axis = dict(
        gridcolor=GLOBAL_CHART_GRID_COLOR,
        zerolinecolor=GLOBAL_CHART_ZERO_COLOR,
        linecolor=GLOBAL_CHART_AXIS_COLOR,
        tickcolor=GLOBAL_CHART_AXIS_COLOR,
        tickfont=dict(family=GLOBAL_DISPLAY_FONT_FAMILY, size=12,
                      color=GLOBAL_MUTED_TEXT_COLOR),
        zeroline=False,
    )
    pio.templates["ow2"] = go.layout.Template(
        layout=dict(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor=GLOBAL_CHART_PLOT_BG,
            font=dict(family=GLOBAL_FONT_FAMILY, size=12, color=GLOBAL_TEXT_COLOR),
            xaxis=axis,
            yaxis=axis,
            hoverlabel=dict(
                bgcolor="#1e222e",
                bordercolor=GLOBAL_ACCENT_COLOR,
                font=dict(family=GLOBAL_FONT_FAMILY, size=12, color=GLOBAL_TEXT_COLOR),
            ),
            legend=dict(
                bgcolor="rgba(18, 20, 33, 0.82)",
                bordercolor="rgba(148, 150, 190, 0.22)",
                borderwidth=1,
            ),
            margin=dict(l=40, r=20, t=20, b=40),
        )
    )
    pio.templates.default = "ow2"


_register_template()
