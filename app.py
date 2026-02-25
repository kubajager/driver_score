"""
grid.online Driver Scorecard – internal support tool.
Search courier by name or driver_id, see segment, rank, metrics, benchmarks, and actionable insights.
"""

from __future__ import annotations

import io
import os
import re
from pathlib import Path
from urllib.request import urlopen

import pandas as pd
import streamlit as st

# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

EXCEL_PATH = Path(__file__).resolve().parent / "data" / "Priority Booking 02-26 results.xlsx"
SHEET_NAMES = ["OOH", "HD Praha", "HD Brno", "HD Ostrava", "HD Olomouc", "HD HK", "HD Plzen"]

# Password for 24/7 internal access (override via SCORECARD_PASSWORD env when deploying)
APP_PASSWORD = os.environ.get("SCORECARD_PASSWORD", "grid.@nline")

METRIC_COLUMNS = [
    "Kvalita doručení",
    "Efektivita jízdy",
    "Zdvojené/otočky",
    "Jízdy Po, Út, Pá",
    "Zpoždění v jízdě",
    "Zpoždění na příjezdu",
    "Delivery Quality",
]

RECOMMENDATIONS: dict[str, str] = {
    "Kvalita doručení": "Důsledněji dodržujte standardy doručování (2× telefonát, min. 20 s vyzvánění, pak fyzický pokus) a hlídejte úspěšnost doručení do boxů s rezervovanou schránkou.",
    "Efektivita jízdy": "Zaměřte se na rychlost nakládky i doručení – efektivita roste se zkušeností, pomůže konzistentní tempo a lepší plánování trasy.",
    "Zpoždění na příjezdu": "Po přijetí jízdy jeďte bezodkladně na depo a minimalizujte zpoždění vůči odhadu v aplikaci.",
    "Zpoždění v jízdě": "Minimalizujte zpoždění během rozvozu – pomůže plynulejší průběh trasy, méně prostojů a rychlé řešení problémů na místě.",
    "Jízdy Po, Út, Pá": "Buďte dostupnější v exponované dny (pondělí, úterý, pátek) – výrazně to zvyšuje užitečnost v regionu.",
    "Zdvojené/otočky": "Využívejte zdvojené jízdy nebo jízdy na otočku, pokud jsou k dispozici.",
    "Delivery Quality": "Důsledněji dodržujte standardy doručování a hlídejte úspěšnost doručení.",
}

WHY_IT_MATTERS: dict[str, str] = {
    "Kvalita doručení": "Kvalita – vyšší úspěšnost doručení zvyšuje spokojenost zákazníků.",
    "Efektivita jízdy": "Produktivita – efektivní jízdy znamenají víc doručení za stejný čas.",
    "Zpoždění na příjezdu": "Kvalita – včasný příjezd na depo zlepšuje plánování rozvozu.",
    "Zpoždění v jízdě": "Kvalita – méně zpoždění během rozvozu zvyšuje spolehlivost.",
    "Jízdy Po, Út, Pá": "Flexibilita – dostupnost v exponované dny zvyšuje využitelnost.",
    "Zdvojené/otočky": "Produktivita – zdvojené jízdy zlepšují využití kapacity.",
    "Delivery Quality": "Kvalita – standardy doručení přímo ovlivňují zkušenost zákazníka.",
}

BRAND_CSS = """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600&display=swap');
  :root {
    --green: #009414;
    --green-bg: rgba(0, 148, 20, 0.15);
    --bg-dark: #12171D;
    --card-dark: #1A2028;
    --text: #F0F2F5;
    --text-secondary: #95A3B6;
    --text-tertiary: #6B7A8F;
    --border: #2D3748;
    --alert: rgba(255, 234, 199, 0.2);
    --error: #F71634;
  }
  .stApp, [data-testid="stAppViewContainer"] { background: var(--bg-dark) !important; }
  .main .block-container { padding-top: 1.5rem; }
  h1, h2, h3 { font-family: 'Space Grotesk', 'Inter', sans-serif !important; color: var(--text) !important; }
  p, span, div, label { font-family: 'Inter', sans-serif !important; color: var(--text); }
  [data-testid="stVerticalBlock"] > div { color: var(--text); }
  .stTextInput label { color: var(--text-secondary) !important; }
  .stSelectbox label { color: var(--text-secondary) !important; }
  .segment-badge {
    display: inline-block;
    padding: 0.25rem 0.6rem;
    border-radius: 6px;
    font-size: 0.85rem;
    font-weight: 500;
    background: var(--green-bg);
    color: var(--green);
    border: 1px solid var(--green);
  }
  .eligibility-top20 { background: var(--green-bg); color: #4ADE80; border-color: var(--green); }
  .eligibility-top50 { background: var(--alert); color: #FCD34D; border-color: #E8D4A0; }
  .eligibility-bottom { background: rgba(255,255,255,0.06); color: var(--text-secondary); border-color: var(--border); }
  .driver-card {
    background: var(--card-dark);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin: 1rem 0;
  }
  .metric-card {
    background: var(--card-dark);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 0.65rem 0.9rem;
    margin: 0.5rem 0;
  }
  .metric-card .metric-name { font-weight: 600; font-size: 0.9rem; color: var(--text); margin-bottom: 0.35rem; }
  .metric-card .metric-vs { font-size: 0.85rem; color: var(--text-secondary); }
  .metric-card .above { color: #4ADE80; font-weight: 500; }
  .metric-card .below { color: #F87171; font-weight: 500; }
  .metric-bar-track {
    height: 20px;
    background: rgba(255,255,255,0.06);
    border-radius: 6px;
    position: relative;
    margin: 0.35rem 0;
  }
  .metric-bar-band { position: absolute; top: 0; bottom: 0; border-radius: 6px; background: var(--green-bg); }
  .metric-bar-median { position: absolute; top: 0; bottom: 0; width: 3px; background: var(--green); border-radius: 2px; transform: translateX(-50%); }
  .metric-bar-courier { position: absolute; top: -4px; bottom: -4px; width: 4px; background: #F0F2F5; border-radius: 2px; transform: translateX(-50%); box-shadow: 0 0 0 1px var(--bg-dark); }
  .metric-bar-labels { display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-tertiary); margin-top: 0.2rem; }
  .metric-legend { font-size: 0.8rem; color: var(--text-tertiary); margin-bottom: 0.5rem; }
  .insight-box { padding: 1rem 1.25rem; border-radius: 10px; margin: 0.75rem 0; border: 1px solid var(--border); color: var(--text); line-height: 1.5; }
  .insight-box .insight-title { font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 0.35rem; }
  .insight-box .insight-metric { font-weight: 600; font-size: 1rem; margin-bottom: 0.25rem; }
  .insight-box .insight-nums { font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 0.5rem; }
  .insight-box .insight-text { font-size: 0.9rem; color: var(--text); }
  .insight-box .insight-why { font-size: 0.85rem; color: var(--text-tertiary); margin-top: 0.4rem; }
  .insight-strength { background: rgba(0, 148, 20, 0.08); border-left: 4px solid var(--green); }
  .insight-strength .insight-title { color: var(--green); }
  .insight-focus { background: rgba(248, 113, 113, 0.08); border-left: 4px solid #F87171; }
  .insight-focus .insight-title { color: #F87171; }
  .data-source-caption { font-size: 0.8rem; color: var(--text-tertiary); margin-top: 0.75rem; }
</style>
"""


# -----------------------------------------------------------------------------
# Data loading & benchmarks
# -----------------------------------------------------------------------------


def _get_excel_bytes() -> bytes | None:
    """Load Excel from local file or from private URL (for deploy). Never put Excel in Git."""
    if EXCEL_PATH.exists():
        return EXCEL_PATH.read_bytes()
    url = os.environ.get("EXCEL_URL")
    if not url and hasattr(st, "secrets"):
        try:
            url = getattr(st.secrets, "excel_url", None) or (st.secrets.get("excel_url") if hasattr(st.secrets, "get") else None)
        except Exception:
            pass
    if not url:
        return None
    try:
        with urlopen(url) as resp:
            return resp.read()
    except Exception:
        return None


@st.cache_data(ttl=300)
def load_all_data() -> pd.DataFrame:
    """Load Excel from local path or from EXCEL_URL / secrets (all sheets); add segment column."""
    data = _get_excel_bytes()
    if data is None:
        return pd.DataFrame()
    frames: list[pd.DataFrame] = []
    for sheet in SHEET_NAMES:
        try:
            df = pd.read_excel(io.BytesIO(data), sheet_name=sheet)
        except Exception:
            continue
        df = df.copy()
        df["segment"] = sheet
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    numeric_cols = ["rank", "drivers_score"] + [c for c in METRIC_COLUMNS if c in out.columns]
    for col in numeric_cols:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    return out


def get_metric_columns_in_df(df: pd.DataFrame) -> list[str]:
    return [c for c in METRIC_COLUMNS if c in df.columns]


def get_benchmark_columns(df: pd.DataFrame) -> list[str]:
    """Columns for which we compute P25/P50/P75 (metrics + drivers_score)."""
    return ["drivers_score"] + get_metric_columns_in_df(df)


def compute_benchmarks_per_sheet(all_data: pd.DataFrame) -> dict[str, dict[str, dict[str, float]]]:
    """Per segment (sheet): for each metric and drivers_score, compute P25, P50, P75."""
    result: dict[str, dict[str, dict[str, float]]] = {}
    for segment in all_data["segment"].unique():
        seg_df = all_data[all_data["segment"] == segment]
        result[segment] = {}
        for col in get_benchmark_columns(seg_df):
            if col not in seg_df.columns:
                continue
            s = seg_df[col].dropna()
            if s.empty:
                result[segment][col] = {"p25": 0.0, "p50": 0.0, "p75": 0.0}
            else:
                result[segment][col] = {
                    "p25": float(s.quantile(0.25)),
                    "p50": float(s.quantile(0.50)),
                    "p75": float(s.quantile(0.75)),
                }
    return result


def get_eligibility(rank: int, total: int) -> tuple[str, str]:
    """Returns (badge_class_suffix, label). Percentile = rank / total (rank 1 = top)."""
    if total <= 0:
        return "bottom", "—"
    pct = rank / total  # rank 1 in 100 => 1%, so top 20% => rank <= 20
    if pct <= 0.20:
        return "top20", "Top 20 %: priority + rezervace"
    if pct <= 0.50:
        return "top50", "Top 50 %: rezervace"
    return "bottom", "Zatím bez rezervací/priorit"


# -----------------------------------------------------------------------------
# Search
# -----------------------------------------------------------------------------


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def search_drivers(all_data: pd.DataFrame, query: str) -> pd.DataFrame:
    """Search by driver_id (exact or partial) or full_name (partial, case-insensitive)."""
    if not query or all_data.empty:
        return pd.DataFrame()
    q = _normalize(query)
    if not q:
        return pd.DataFrame()

    def matches(row: pd.Series) -> bool:
        name = _normalize(str(row.get("full_name", "")))
        did = str(row.get("driver_id", "")).strip().lower()
        return q in name or q in did or (q.isdigit() and did == q)

    mask = all_data.apply(matches, axis=1)
    return all_data[mask].copy()


# -----------------------------------------------------------------------------
# Insights (strengths & focus)
# -----------------------------------------------------------------------------


def get_insights(
    row: pd.Series,
    benchmarks: dict[str, dict[str, float]],
    metric_cols: list[str],
) -> tuple[list[tuple[str, float, dict]], list[tuple[str, float, dict]]]:
    """
    Returns (strengths, focus_next).
    Each item: (metric_name, driver_value, {p25, p50, p75, delta_to_median, recommendation}).
    """
    strengths: list[tuple[str, float, dict]] = []
    focus: list[tuple[str, float, dict]] = []
    deltas: list[tuple[str, float, float]] = []  # (metric, value, delta_to_median)

    for col in metric_cols:
        val = row.get(col)
        if pd.isna(val):
            continue
        try:
            v = float(val)
        except (TypeError, ValueError):
            continue
        b = benchmarks.get(col, {})
        p50 = b.get("p50") or 0
        delta = v - p50
        deltas.append((col, v, delta))

    if not deltas:
        return strengths, focus

    deltas.sort(key=lambda x: x[2], reverse=True)
    for col, v, delta in deltas[:2]:
        b = benchmarks.get(col, {})
        strengths.append((col, v, {**b, "delta_to_median": delta, "recommendation": RECOMMENDATIONS.get(col, "")}))
    for col, v, delta in deltas[-3:][::-1]:
        b = benchmarks.get(col, {})
        focus.append((col, v, {**b, "delta_to_median": delta, "recommendation": RECOMMENDATIONS.get(col, "")}))

    return strengths, focus


# -----------------------------------------------------------------------------
# UI
# -----------------------------------------------------------------------------


def apply_brand():
    st.markdown(BRAND_CSS, unsafe_allow_html=True)
    st.markdown(
        """<h1 style="color: #009414;">grid.online Driver Scorecard</h1>
        <p style="color: #95A3B6;">Vyhledejte kurýra podle jména nebo driver_id.</p>""",
        unsafe_allow_html=True,
    )


def _scale_positions(
    driver_val: float, p25: float, p50: float, p75: float
) -> tuple[float, float, float, float]:
    """Return (pos_driver, pos_p25, pos_p50, pos_p75) in 0..1 for horizontal bar."""
    lo = min(p25, p75, driver_val)
    hi = max(p25, p75, driver_val)
    span = hi - lo if hi > lo else 1
    display_min = lo - 0.08 * span
    display_max = hi + 0.08 * span
    display_span = display_max - display_min or 1
    def pos(x: float) -> float:
        return max(0, min(1, (x - display_min) / display_span))
    return pos(driver_val), pos(p25), pos(p50), pos(p75)


def _as_percentage(x: float) -> float:
    """If x is in 0–1 (decimal from Excel), return as percentage 0–100; else return as-is (already %)."""
    if 0 <= x <= 1:
        return x * 100
    return x


def render_metric_card(
    col: str,
    driver_val: float,
    p25: float,
    p50: float,
    p75: float,
    *,
    value_suffix: str = "",
) -> None:
    """One metric: name, courier vs median (above/below), and P25/P50/P75 bar with labels.
    value_suffix: e.g. ' %' for percentage metrics (Delivery Quality) – display only, values stay as-is."""
    above_median = driver_val >= p50
    pos_driver, pos_p25, pos_p50, pos_p75 = _scale_positions(driver_val, p25, p50, p75)
    band_left = min(pos_p25, pos_p75) * 100
    band_width = abs(pos_p75 - pos_p25) * 100
    status_class = "above" if above_median else "below"
    status_text = "Nad mediánem" if above_median else "Pod mediánem"
    suf = value_suffix
    st.markdown(
        f"""
        <div class="metric-card">
          <div class="metric-name">{col}</div>
          <div class="metric-vs">
            Kurýr: <strong style="color: var(--text);">{driver_val:.1f}{suf}</strong>
            &nbsp;·&nbsp; Medián: <strong>{p50:.1f}{suf}</strong>
            &nbsp;·&nbsp; <span class="{status_class}">{status_text}</span>
          </div>
          <div class="metric-bar-track">
            <div class="metric-bar-band" style="left: {band_left:.1f}%; width: {band_width:.1f}%;"></div>
            <div class="metric-bar-median" style="left: {pos_p50*100:.1f}%;"></div>
            <div class="metric-bar-courier" style="left: {pos_driver*100:.1f}%;"></div>
          </div>
          <div class="metric-bar-labels">
            <span>P25: {p25:.1f}{suf}</span>
            <span>Medián: {p50:.1f}{suf}</span>
            <span>P75: {p75:.1f}{suf}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(page_title="Driver Scorecard | grid.online", layout="wide", initial_sidebar_state="collapsed")

    # Password gate: required for 24/7 internal access
    if not st.session_state.get("authenticated"):
        apply_brand()
        st.markdown("---")
        pwd = st.text_input("Heslo", type="password", placeholder="Zadejte heslo…", key="pwd_input", label_visibility="visible")
        col1, _ = st.columns([1, 3])
        with col1:
            if st.button("Přihlásit", type="primary"):
                if pwd == APP_PASSWORD:
                    st.session_state["authenticated"] = True
                    st.rerun()
                else:
                    st.error("Nesprávné heslo.")
        st.stop()

    apply_brand()

    all_data = load_all_data()
    if all_data.empty:
        st.warning(
            "Data nenalezena. Lokálně: umístěte **Priority Booking 02-26 results.xlsx** do složky `data/`. "
            "Při nasazení: nastavte v Secrets nebo env proměnnou **EXCEL_URL** na soukromý odkaz na soubor (Excel nesmí být v Gitu)."
        )
        st.stop()

    benchmarks_by_sheet = compute_benchmarks_per_sheet(all_data)
    metric_cols = get_metric_columns_in_df(all_data)

    query = st.text_input("Hledat kurýra (jméno nebo driver_id)", placeholder="Příjmení nebo ID…", key="search")
    selected_key = st.session_state.get("selected_driver_key")

    matches = search_drivers(all_data, query) if query else pd.DataFrame()

    if matches.empty and query:
        st.info("Žádný kurýr nevyhovuje hledání.")
        if selected_key:
            del st.session_state["selected_driver_key"]
        st.stop()

    if not query:
        if selected_key:
            del st.session_state["selected_driver_key"]
        st.info("Zadejte jméno nebo driver_id pro vyhledání.")
        st.stop()

    if len(matches) == 1:
        selected = matches.iloc[0]
        selected_key = None
    else:
        def driver_key(r: pd.Series) -> str:
            return f"{r.get('driver_id', '')}|{r.get('segment', '')}"
        match_keys = [driver_key(matches.iloc[i]) for i in range(len(matches))]
        if selected_key and selected_key in match_keys:
            idx = match_keys.index(selected_key)
            selected = matches.iloc[idx]
        else:
            options = [
                f"{row.get('full_name', '—')} | {row.get('driver_id', '—')} | {row.get('working_city', '—')} | {row.get('segment', '—')}"
                for _, row in matches.iterrows()
            ]
            choice = st.selectbox(
                "Vyberte kurýra",
                range(len(options)),
                format_func=lambda i: options[i],
                key="driver_select",
            )
            selected = matches.iloc[choice]
            selected_key = driver_key(selected)
        st.session_state["selected_driver_key"] = selected_key

    segment = selected.get("segment", "")
    benchmarks = benchmarks_by_sheet.get(segment, {})
    total_in_segment = int(all_data[all_data["segment"] == segment].shape[0])
    rank = int(selected.get("rank", 0))
    elig_class, elig_label = get_eligibility(rank, total_in_segment)

    strengths, focus = get_insights(selected, benchmarks, metric_cols)

    # One-line summary
    summary_parts = [elig_label + "."]
    if strengths:
        summary_parts.append(f"Nejsilnější v {strengths[0][0]}.")
    if focus:
        summary_parts.append(f"Zlepšit: {focus[0][0]}.")
    one_line_summary = " ".join(summary_parts)

    # Percentile: better than X% of drivers in segment (rank 1 = best)
    pct_better = round((total_in_segment - rank) / total_in_segment * 100) if total_in_segment > 0 else 0

    st.markdown("---")
    st.markdown(
        f"""
        <div class="driver-card">
          <div style="display: flex; flex-wrap: wrap; align-items: center; gap: 0.75rem;">
            <span style="font-size: 1.25rem; font-weight: 600; color: #F0F2F5;">{selected.get('full_name', '—')}</span>
            <span class="segment-badge">{segment}</span>
            <span style="color: #95A3B6;">ID: {selected.get('driver_id', '—')}</span>
            <span style="color: #95A3B6;">Pořadí: {rank} / {total_in_segment} (segment {segment})</span>
            <span style="font-weight: 600; color: #009414;">Celkové hodnocení kurýra: {selected.get('drivers_score', '—')}</span>
            <span class="segment-badge eligibility-{elig_class}">{elig_label}</span>
            <span style="color: var(--text-tertiary); font-size: 0.9rem;">Lepší než {pct_better} % kurýrů v segmentu</span>
          </div>
          <p style="margin: 0.75rem 0 0; color: var(--text-secondary); font-size: 0.9rem;">{one_line_summary}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("#### Metriky: hodnota kurýra vs medián (P25, medián, P75)")
    st.markdown(
        '<p class="metric-legend">Pruh: zelená čára = medián, bílá čárka = kurýr, zelený pás = rozsah P25–P75.</p>',
        unsafe_allow_html=True,
    )
    # Celkové hodnocení kurýra (drivers_score) on a single full-width line
    if "drivers_score" in benchmarks:
        b = benchmarks.get("drivers_score", {})
        val_f = float(selected.get("drivers_score", 0)) if pd.notna(selected.get("drivers_score")) else 0
        render_metric_card("Celkové hodnocení kurýra", val_f, b.get("p25", 0), b.get("p50", 0), b.get("p75", 0))
    # Additional metrics: two rows of three boxes
    chunk_size = 3
    for i in range(0, len(metric_cols), chunk_size):
        chunk = metric_cols[i : i + chunk_size]
        cols = st.columns(len(chunk))
        for j, col_name in enumerate(chunk):
            val = selected.get(col_name)
            b = benchmarks.get(col_name, {})
            p25 = b.get("p25", 0)
            p50 = b.get("p50", 0)
            p75 = b.get("p75", 0)
            val_f = float(val) if pd.notna(val) else 0
            with cols[j]:
                if col_name == "Delivery Quality":
                    # Excel stores 0–1 decimal (e.g. 0.85 = 85%); convert to 0–100 for display
                    val_f = _as_percentage(val_f)
                    p25, p50, p75 = _as_percentage(p25), _as_percentage(p50), _as_percentage(p75)
                    render_metric_card(col_name, val_f, p25, p50, p75, value_suffix=" %")
                else:
                    render_metric_card(col_name, val_f, p25, p50, p75)
    st.markdown(
        '<p class="data-source-caption">Všechny metriky včetně „Delivery Quality“ pocházejí ze sloupců v souboru Excel (Priority Booking results). '
        '„Delivery Quality“ = sloupec v exportu (hodnoty 0–1 se zobrazí jako 0–100 %). Pokud sloupec chybí nebo je prázdný, zobrazí se 0.</p>',
        unsafe_allow_html=True,
    )

    st.markdown("#### Silné stránky")
    if strengths:
        for name, v, d in strengths:
            p50 = d.get("p50", 0)
            if name == "Delivery Quality":
                v, p50 = _as_percentage(v), _as_percentage(p50)
                suf = " %"
            else:
                suf = ""
            st.markdown(
                f'<div class="insight-box insight-strength">'
                f'<div class="insight-title">Silná stránka</div>'
                f'<div class="insight-metric">{name}</div>'
                f'<div class="insight-nums">Kurýr: <strong>{v:.2f}{suf}</strong> · medián: {p50:.2f}{suf} (nad mediánem)</div>'
                f'<div class="insight-text">{d.get("recommendation", "")}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Žádné výrazné silné stránky proti mediánu.")

    st.markdown("#### Doporučení (na co se zaměřit)")
    if focus:
        for name, v, d in focus:
            p50 = d.get("p50", 0)
            p75 = d.get("p75", 0)
            why = WHY_IT_MATTERS.get(name, "")
            if name == "Delivery Quality":
                v, p50, p75 = _as_percentage(v), _as_percentage(p50), _as_percentage(p75)
                suf = " %"
            else:
                suf = ""
            st.markdown(
                f'<div class="insight-box insight-focus">'
                f'<div class="insight-title">K zlepšení</div>'
                f'<div class="insight-metric">{name}</div>'
                f'<div class="insight-nums">Kurýr: <strong>{v:.2f}{suf}</strong> · medián: {p50:.2f}{suf} · lepší kvartil: {p75:.2f}{suf} (pod mediánem)</div>'
                f'<div class="insight-text">{d.get("recommendation", "")}</div>'
                f'<div class="insight-why">{why}</div>'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Všechny metriky na úrovni nebo nad mediánem.")


if __name__ == "__main__":
    main()
