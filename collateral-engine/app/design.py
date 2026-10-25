"""Shared look of the console: CSS and small HTML components used by every page.

Every text passed in is escaped here, so callers pass plain strings.
"""

import html
from dataclasses import dataclass
from enum import StrEnum

import streamlit as st

STYLES = """
<style>
:root{
  --ink:#0f1f3d; --muted:rgba(15,31,61,.62); --line:rgba(15,31,61,.12);
  --surface:#ffffff; --tint:#f4f6fb; --brand:#16337a; --brand-soft:rgba(22,51,122,.08);
  --good:#1f9d55; --warn:#b7791f; --bad:#c53030; --info:#2563eb;
}
.block-container{padding-top:1.6rem;max-width:1320px}
section[data-testid="stSidebar"]{min-width:340px}
/* A moving bar at the top of the page while the app works, so a slow step never looks frozen. */
[data-test-script-state="running"]::before{content:"";position:fixed;top:0;left:0;right:0;
  height:3px;z-index:999999;background:linear-gradient(90deg,transparent,#2b6cb0,#16337a,
  transparent);background-size:40% 100%;background-repeat:no-repeat;
  animation:loading-bar 1.1s linear infinite}
@keyframes loading-bar{from{background-position:-40% 0}to{background-position:140% 0}}
[data-testid="stSidebarNav"] a span{white-space:normal}
.hero{background:linear-gradient(135deg,#16337a 0%,#1e4fa8 60%,#2b6cb0 100%);color:#fff;
  border-radius:18px;padding:30px 34px;margin:4px 0 22px}
.hero h1{color:#fff;font-size:2.15rem;line-height:1.15;margin:0 0 10px;padding:0}
.hero p{color:rgba(255,255,255,.88);font-size:1.05rem;margin:0 0 16px;max-width:900px}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{background:rgba(255,255,255,.14);border:1px solid rgba(255,255,255,.28);color:#fff;
  border-radius:999px;padding:4px 12px;font-size:13px;font-weight:600}
.chip.light{background:var(--brand-soft);border-color:transparent;color:var(--brand)}
.section-title{font-size:1.25rem;font-weight:700;color:var(--ink);margin:26px 0 4px}
.section-lead{color:var(--muted);margin:0 0 14px;font-size:.98rem}
.flow{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin:8px 0 6px}
.step{background:var(--surface);border:1px solid var(--line);border-radius:14px;
  padding:16px 16px 14px;position:relative}
.step .num{display:inline-flex;align-items:center;justify-content:center;width:28px;
  height:28px;border-radius:50%;background:var(--brand);color:#fff;font-weight:700;
  font-size:14px;margin-right:8px}
.step .head{display:flex;align-items:center;font-weight:700;color:var(--ink);margin-bottom:8px}
.step .body{color:var(--muted);font-size:.92rem;line-height:1.45}
.step .tag{margin-top:10px;display:inline-block;font-size:12px;font-weight:600;
  color:var(--brand);background:var(--brand-soft);border-radius:6px;padding:2px 8px}
.cards{display:grid;grid-template-columns:repeat(var(--columns,4),1fr);gap:12px;margin:6px 0 10px}
.stat{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.stat .label{color:var(--muted);font-size:.84rem;margin-bottom:4px}
.stat .value{color:var(--ink);font-size:1.55rem;font-weight:700;line-height:1.2;
  overflow-wrap:anywhere}
.stat .note{color:var(--muted);font-size:.8rem;margin-top:4px}
.stat.good{border-top:4px solid var(--good)} .stat.warn{border-top:4px solid var(--warn)}
.stat.bad{border-top:4px solid var(--bad)} .stat.brand{border-top:4px solid var(--brand)}
.verdict{border-left:6px solid var(--verdict);background:var(--tint);
  border-radius:12px;padding:16px 20px;margin:6px 0 14px}
.verdict h3{margin:0 0 6px;color:var(--verdict)}
.reason{padding:4px 0;font-size:15px}
.pill{display:inline-block;padding:1px 9px;border-radius:999px;font-size:12px;font-weight:700;
  color:#fff;margin-right:8px}
.small{font-size:13px;opacity:.8}
.verdict .why{color:var(--ink);font-size:1rem;margin:4px 0 0}
.limits{background:var(--surface);border:1px solid var(--line);border-radius:14px;
  padding:16px 18px;margin:4px 0 16px}
.limit-row{display:grid;grid-template-columns:230px 1fr 150px;align-items:center;gap:12px;
  margin:9px 0}
.limit-row .name{font-size:.92rem;color:var(--ink)}
.limit-row .name small{display:block;color:var(--muted);font-size:.78rem}
.limit-row .track{height:14px;border-radius:7px;background:rgba(15,31,61,.07);position:relative}
.limit-row .fill{position:absolute;left:0;top:0;bottom:0;border-radius:7px}
.limit-row .amount{text-align:right;font-weight:700;color:var(--ink);
  font-variant-numeric:tabular-nums}
.limit-row.binding .name{font-weight:700}
.limit-row .beyond{position:absolute;right:0;top:-17px;font-size:11px;color:var(--muted)}
.guarantees{display:grid;grid-template-columns:repeat(2,1fr);gap:10px;margin:6px 0}
.guarantee{background:var(--tint);border-radius:12px;padding:12px 14px;font-size:.93rem;
  color:var(--ink)}
.guarantee b{display:block;margin-bottom:2px}
.setup-step{font-weight:700;color:var(--brand);font-size:.95rem;margin-bottom:4px}
.profile{font-size:.9rem;color:var(--ink);line-height:1.6;padding-bottom:6px}
.profile span{color:var(--muted)}
[data-testid="stPageLink"] a{border:1px solid var(--line);border-radius:12px;
  padding:10px 14px;background:var(--surface)}
[data-testid="stPageLink"] a:hover{border-color:var(--brand);background:var(--brand-soft)}
.empty{border:1.5px dashed var(--line);border-radius:14px;padding:26px;text-align:center;
  color:var(--muted);margin:10px 0}
.stages{display:grid;grid-template-columns:repeat(5,1fr);gap:10px;margin:8px 0 14px}
.stage{background:var(--surface);border:1px solid var(--line);border-top:4px solid var(--stage);
  border-radius:12px;padding:12px 14px}
.stage .name{font-weight:700;color:var(--ink);font-size:.95rem;margin-bottom:6px}
.stage .status{display:inline-block;color:#fff;background:var(--stage);border-radius:999px;
  padding:1px 10px;font-size:12px;font-weight:700}
.stage .meta{color:var(--muted);font-size:.76rem;margin-top:8px;line-height:1.35}
.source-badge{display:inline-block;background:var(--brand-soft);color:var(--brand);
  border-radius:8px;padding:3px 10px;font-size:.82rem;font-weight:600;margin:2px 0 6px}
.cards.compact .stat{padding:10px 14px}
.cards.compact .stat .value{font-size:1.02rem;font-weight:650}
.form-subhead{font-weight:700;color:var(--ink);font-size:1rem;margin:18px 0 4px;
  padding-top:14px;border-top:1px solid var(--line)}
.form-subhead small{display:block;font-weight:400;color:var(--muted);font-size:.84rem;
  margin-top:2px}
.range{position:relative;height:64px;margin:30px 6px 4px}
.range .track{position:absolute;top:22px;left:0;right:0;height:6px;border-radius:3px;
  background:rgba(15,31,61,.1)}
.range .band{position:absolute;top:16px;height:18px;border-radius:9px;
  background:rgba(37,99,235,.35)}
.range .mark{position:absolute;top:8px;width:3px;height:34px;border-radius:2px}
.range .tag{position:absolute;top:44px;transform:translateX(-50%);font-size:12px;
  white-space:nowrap}
.range .tag.above{top:-12px}
.subtitle{font-weight:700;color:var(--ink);font-size:1.02rem;margin:18px 0 6px}
.verdict .why-list{margin:10px 0 0;padding-left:20px;color:var(--ink);font-size:.95rem}
.verdict .why-list li{margin:3px 0}
.ai-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:14px 0 4px}
.ai-head .title{font-weight:700;color:var(--ink);font-size:1.12rem}
.ai-chip{background:linear-gradient(90deg,#16337a,#2b6cb0);color:#fff;border-radius:999px;
  padding:2px 11px;font-weight:800;font-size:.78rem;letter-spacing:.04em}
.ai-model{color:var(--brand);background:var(--brand-soft);border-radius:8px;padding:2px 9px;
  font-size:.8rem;font-weight:600}
.ai-note{color:var(--muted);font-size:.84rem;margin:0 0 8px}
.lv-card{background:radial-gradient(120% 160% at 0% 0%,#1e3a8a 0%,#0f1f3d 55%,#081430 100%);
  color:#fff;border-radius:16px;padding:18px 20px;margin:6px 0 12px}
.lv-head{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.lv-head .title{font-weight:700;font-size:1.08rem}
.lv-status{background:var(--lv);color:#fff;border-radius:999px;padding:3px 12px;font-weight:800;
  font-size:.82rem;letter-spacing:.02em}
.lv-summary{color:rgba(255,255,255,.74);font-size:.9rem;margin:6px 0 12px}
.lv-strip{display:grid;grid-template-columns:repeat(var(--count,3),minmax(0,1fr));gap:12px}
.lv-frame{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.14);
  border-radius:12px;overflow:hidden}
.lv-frame.done{border-color:rgba(34,197,94,.55)} .lv-frame.missed{border-color:rgba(239,68,68,.55)}
.lv-frame img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover;transform:scaleX(-1)}
.lv-frame .no-frame{aspect-ratio:4/3;display:flex;align-items:center;justify-content:center;
  font-size:2rem;color:#f87171;background:rgba(239,68,68,.08)}
.lv-frame .meta{padding:8px 10px;font-size:.86rem;line-height:1.35}
.lv-frame .state{font-weight:700} .lv-frame.done .state{color:#4ade80}
.lv-frame.missed .state{color:#f87171}
.lv-frame .hash{display:block;font-family:ui-monospace,Menlo,monospace;font-size:.7rem;
  color:rgba(255,255,255,.55);margin-top:2px}
.lv-issues{margin:12px 0 0;padding-left:18px;color:#fcd34d;font-size:.9rem}
.lv-note{color:rgba(255,255,255,.6);font-size:.8rem;margin:12px 0 0}
@media (max-width: 900px){
  .flow{grid-template-columns:1fr 1fr} .cards{grid-template-columns:1fr 1fr}
  .stages{grid-template-columns:1fr 1fr} .lv-strip{grid-template-columns:1fr 1fr}
  .guarantees{grid-template-columns:1fr} .limit-row{grid-template-columns:1fr}
  .limit-row .amount{text-align:left}
}
</style>
"""


class Tone(StrEnum):
    GOOD = "good"
    WARN = "warn"
    BAD = "bad"
    BRAND = "brand"
    PLAIN = ""


@dataclass(frozen=True)
class Stat:
    label: str
    value: str
    note: str = ""
    tone: Tone = Tone.PLAIN


@dataclass(frozen=True)
class FlowStep:
    title: str
    body: str
    tag: str


@dataclass(frozen=True)
class LimitBar:
    name: str
    detail: str
    amount: float | None
    amount_text: str
    colour: str
    is_binding: bool = False


@dataclass(frozen=True)
class LivenessFrame:
    title: str
    state: str
    is_completed: bool
    image_data_url: str | None
    sha256: str | None


@dataclass(frozen=True)
class LivenessCard:
    title: str
    status: str
    colour: str
    summary: str
    frames: list[LivenessFrame]
    issues: list[str]
    note: str


@dataclass(frozen=True)
class StageCard:
    name: str
    status: str
    colour: str
    meta: str


def apply_styles() -> None:
    st.markdown(STYLES, unsafe_allow_html=True)


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def hero(title: str, lead: str, chips: list[str]) -> None:
    chip_html = "".join(f'<span class="chip">{_escape(chip)}</span>' for chip in chips)
    st.markdown(
        f'<div class="hero"><h1>{_escape(title)}</h1><p>{_escape(lead)}</p>'
        f'<div class="chips">{chip_html}</div></div>',
        unsafe_allow_html=True,
    )


def section(title: str, lead: str = "") -> None:
    lead_html = f'<p class="section-lead">{_escape(lead)}</p>' if lead else ""
    st.markdown(
        f'<div class="section-title">{_escape(title)}</div>{lead_html}', unsafe_allow_html=True
    )


def flow(steps: list[FlowStep]) -> None:
    items = "".join(
        f'<div class="step"><div class="head"><span class="num">{index}</span>'
        f'{_escape(step.title)}</div><div class="body">{_escape(step.body)}</div>'
        f'<span class="tag">{_escape(step.tag)}</span></div>'
        for index, step in enumerate(steps, start=1)
    )
    st.markdown(f'<div class="flow">{items}</div>', unsafe_allow_html=True)


def stat_cards(stats: list[Stat], columns: int = 4, is_compact: bool = False) -> None:
    items = "".join(
        f'<div class="stat {stat.tone}"><div class="label">{_escape(stat.label)}</div>'
        f'<div class="value">{_escape(stat.value)}</div>'
        + (f'<div class="note">{_escape(stat.note)}</div>' if stat.note else "")
        + "</div>"
        for stat in stats
    )
    compact = " compact" if is_compact else ""
    st.markdown(
        f'<div class="cards{compact}" style="--columns:{columns}">{items}</div>',
        unsafe_allow_html=True,
    )


def verdict(
    caption: str, title: str, explanation: str, colour: str, reasons: list[str] | None = None
) -> None:
    reason_items = "".join(f"<li>{_escape(reason)}</li>" for reason in reasons or [])
    reason_html = f'<ul class="why-list">{reason_items}</ul>' if reason_items else ""
    st.markdown(
        f'<div class="verdict" style="--verdict:{colour}">'
        f'<div class="small">{_escape(caption)}</div><h3>{_escape(title)}</h3>'
        f'<p class="why">{_escape(explanation)}</p>{reason_html}</div>',
        unsafe_allow_html=True,
    )


def ai_header(title: str, model: str, note: str) -> None:
    """Marks a section whose evidence comes from a vision model, and names the model."""
    model_html = f'<span class="ai-model">{_escape(model)}</span>' if model else ""
    st.markdown(
        f'<div class="ai-head"><span class="ai-chip">AI</span><span class="title">'
        f"{_escape(title)}</span>{model_html}</div>"
        f'<p class="ai-note">{_escape(note)}</p>',
        unsafe_allow_html=True,
    )


def limit_bars(bars: list[LimitBar], scale_max: float, beyond_label: str) -> None:
    """Horizontal bars on one scale; an amount beyond the scale is drawn full with a marker."""
    rows = "".join(_limit_row(bar, scale_max, beyond_label) for bar in bars)
    st.markdown(f'<div class="limits">{rows}</div>', unsafe_allow_html=True)


def _limit_row(bar: LimitBar, scale_max: float, beyond_label: str) -> str:
    share = 0.0 if bar.amount is None or scale_max <= 0 else min(bar.amount / scale_max, 1.0)
    is_beyond = bar.amount is not None and bar.amount > scale_max
    beyond = f'<span class="beyond">{_escape(beyond_label)} ▸</span>' if is_beyond else ""
    binding = " binding" if bar.is_binding else ""
    return (
        f'<div class="limit-row{binding}"><div class="name">{_escape(bar.name)}'
        f"<small>{_escape(bar.detail)}</small></div>"
        f'<div class="track"><div class="fill" style="width:{share * 100:.1f}%;'
        f'background:{bar.colour}"></div>{beyond}</div>'
        f'<div class="amount">{_escape(bar.amount_text)}</div></div>'
    )


def guarantees(items: list[tuple[str, str]]) -> None:
    cards = "".join(
        f'<div class="guarantee"><b>{_escape(title)}</b>{_escape(body)}</div>'
        for title, body in items
    )
    st.markdown(f'<div class="guarantees">{cards}</div>', unsafe_allow_html=True)


def empty_state(text: str) -> None:
    st.markdown(f'<div class="empty">{_escape(text)}</div>', unsafe_allow_html=True)


def stage_strip(cards: list[StageCard]) -> None:
    items = "".join(
        f'<div class="stage" style="--stage:{card.colour}"><div class="name">'
        f'{_escape(card.name)}</div><span class="status">{_escape(card.status)}</span>'
        f'<div class="meta">{_escape(card.meta)}</div></div>'
        for card in cards
    )
    st.markdown(f'<div class="stages">{items}</div>', unsafe_allow_html=True)


def source_badge(text: str) -> None:
    st.markdown(f'<span class="source-badge">{_escape(text)}</span>', unsafe_allow_html=True)


def form_subhead(title: str, hint: str = "") -> None:
    hint_html = f"<small>{_escape(hint)}</small>" if hint else ""
    st.markdown(
        f'<div class="form-subhead">{_escape(title)}{hint_html}</div>', unsafe_allow_html=True
    )


def subtitle(text: str) -> None:
    st.markdown(f'<div class="subtitle">{_escape(text)}</div>', unsafe_allow_html=True)


def liveness_card(card: LivenessCard) -> None:
    """The liveness session: status, then one evidence frame per task with its SHA-256."""
    frames = "".join(_liveness_frame(frame) for frame in card.frames)
    issues = "".join(f"<li>{_escape(issue)}</li>" for issue in card.issues)
    issues_html = f'<ul class="lv-issues">{issues}</ul>' if issues else ""
    strip_html = (
        f'<div class="lv-strip" style="--count:{len(card.frames)}">{frames}</div>' if frames else ""
    )
    st.markdown(
        f'<div class="lv-card"><div class="lv-head">'
        f'<span class="lv-status" style="--lv:{card.colour}">{_escape(card.status)}</span>'
        f'<span class="title">{_escape(card.title)}</span></div>'
        f'<p class="lv-summary">{_escape(card.summary)}</p>{strip_html}{issues_html}'
        f'<p class="lv-note">{_escape(card.note)}</p></div>',
        unsafe_allow_html=True,
    )


def _liveness_frame(frame: LivenessFrame) -> str:
    image = (
        f'<img src="{_escape(frame.image_data_url)}" alt="">'
        if frame.image_data_url
        else '<div class="no-frame">✕</div>'
    )
    tone = "done" if frame.is_completed else "missed"
    sha = f'<span class="hash">SHA-256 {_escape(frame.sha256[:16])}…</span>' if frame.sha256 else ""
    return (
        f'<div class="lv-frame {tone}">{image}<div class="meta">{_escape(frame.title)}<br>'
        f'<span class="state">{_escape(frame.state)}</span>{sha}</div></div>'
    )

