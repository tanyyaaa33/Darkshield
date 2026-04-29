"""Premium-style Streamlit dashboard for DarkShield transparency analytics."""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from api.routes import EXPLANATIONS
from ml.analysis.ab_test_detector import detect_ab_testing
from ml.compliance.regulatory_mapper import get_compliance_tags
from ml.database.site_scorer import get_vertical_comparison
from ml.database.transparency_db import aggregate_stats, fetch_all_sites, fetch_detections_for_domain, get_score_history

DB_PATH = Path(_ROOT / "data" / "darkshield.db")
EVAL_SUMMARY = _ROOT / "ml" / "models" / "saved" / "eval_results" / "summary.json"

PATTERN_LABELS = {
    "fake_urgency": "Urgency pressure",
    "confirm_shaming": "Guilt-based persuasion",
    "hidden_costs": "Late fee reveal",
    "visual_interference": "Interface distraction",
    "sneaking": "Sneaky additions",
    "forced_continuity": "Auto-renew pressure",
    "misdirection": "Attention steering",
    "social_proof_manipulation": "Trust signal manipulation",
    "bait_and_switch": "Offer mismatch",
    "roach_motel": "Hard to exit flow",
    "none": "No strong pattern",
}

PATTERN_EXAMPLES = {
    "fake_urgency": "Only 2 left! Offer ends in 00:10:00.",
    "confirm_shaming": "No thanks, I prefer paying full price.",
    "hidden_costs": "Extra convenience fee appears at checkout.",
    "visual_interference": "Cancel button is tiny and low contrast.",
    "sneaking": "Protection plan is pre-selected in cart.",
    "forced_continuity": "Free trial now, auto-renews next month.",
    "misdirection": "Skip option is hidden below promotional banners.",
    "social_proof_manipulation": "99 people bought this in the last hour.",
    "bait_and_switch": "Listed price changes once payment starts.",
    "roach_motel": "Subscribe in one click; cancellation buried in settings.",
}


def _conn():
    return sqlite3.connect(DB_PATH)


def _human_pattern(label: str) -> str:
    return PATTERN_LABELS.get(label, label.replace("_", " ").title())


def _risk_label(score: float) -> tuple[str, str]:
    if score <= 30:
        return ("Low risk", "#00d58a")
    if score <= 60:
        return ("Moderate risk", "#ffbe3d")
    if score <= 80:
        return ("High risk", "#ff7a3d")
    return ("Severe risk", "#ff4f6d")


def _top_patterns_text(patterns: pd.Series) -> str:
    if patterns.empty:
        return "No patterns detected yet."
    return ", ".join(_human_pattern(p) for p in patterns.head(3).index)


st.set_page_config(page_title="DarkShield Intelligence", layout="wide")
st.markdown(
    """
<style>
  :root {
    --bg: #10141d;
    --card: #171d29;
    --border: #2a3345;
    --text: #e8edf5;
    --muted: #9ba8bd;
    --green: #00d58a;
    --yellow: #ffbe3d;
    --red: #ff4f6d;
  }
  .stApp { background: radial-gradient(900px 400px at 20% -10%, #1f2a3d 0%, var(--bg) 45%), var(--bg); color: var(--text); }
  h1, h2, h3 { letter-spacing: -0.02em; }
  .ds-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.00));
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px 18px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.20);
    margin-bottom: 12px;
  }
  .ds-eyebrow { color: var(--muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; }
  .ds-help { color: var(--muted); font-size: 0.92rem; margin-top: 4px; }
  .ds-kpi { font-size: 1.75rem; font-weight: 700; margin: 6px 0 0; }
  .ds-divider { border-top: 1px solid var(--border); margin: 12px 0 8px; }
</style>
""",
    unsafe_allow_html=True,
)

st.title("DarkShield Intelligence Dashboard")
st.caption("A clear view of persuasion tactics detected across Indian e-commerce interfaces.")

page = st.sidebar.radio(
    "Sections",
    [
        "Leaderboard",
        "Data Collection & Observations",
        "Vertical Analysis",
        "Site Deep Dive",
        "Full Pattern Report",
        "A/B Test Detection",
        "Statistics",
    ],
)
st.sidebar.caption("DarkShield local transparency workspace")
show_advanced = st.sidebar.toggle(
    "Show advanced visualizations",
    value=False,
    help="Turn this on if you want deeper plots. Keep it off for a simpler walkthrough.",
)

if page == "Leaderboard":
    with st.expander("What is DarkShield?"):
        st.markdown(
            """
- **What this means:** DarkShield finds persuasive UI patterns and tracks them over time.
- **Why it matters:** Manipulative prompts can pressure users into choices they did not intend.
- **Example:** "Only 1 left" + hidden cancellation path can increase pressured purchases.
"""
        )

    with st.expander("How to read this dashboard"):
        st.markdown(
            """
1. Start with **Leaderboard** to see highest-risk domains.
2. Open **Site Deep Dive** to inspect pattern mix and snippets.
3. Use **Full Pattern Report** for definitions and regulatory context.
4. Use **A/B Test Detection** to check if messaging changes across sessions.
"""
        )

if page == "Leaderboard":
    st.subheader("Risk Leaderboard")
    st.caption("Compare domains by overall manipulation score and pattern volume.")
    vertical = st.selectbox("Filter by vertical", ["all", "travel", "fmcg", "fashion", "electronics", "food_delivery"])
    sites = fetch_all_sites(DB_PATH)
    df = pd.DataFrame(sites)
    if not df.empty and vertical != "all":
        df = df[df["vertical"] == vertical]

    if df.empty:
        st.info("No data available yet. Run `python ml/models/evaluate.py` first.")
    else:
        top = df.sort_values("manipulation_score", ascending=False).head(20)
        avg_score = float(top["manipulation_score"].mean())
        risk_text, risk_color = _risk_label(avg_score)
        total_patterns = int(top["total_patterns_found"].sum())
        c1, c2, c3 = st.columns(3)
        c1.markdown(
            f"<div class='ds-card'><div class='ds-eyebrow'>Total Score</div><div class='ds-kpi'>{avg_score:.1f}</div><div class='ds-help'>What this means: average risk in current view.</div></div>",
            unsafe_allow_html=True,
        )
        c2.markdown(
            f"<div class='ds-card'><div class='ds-eyebrow'>Risk Level</div><div class='ds-kpi' style='color:{risk_color}'>{risk_text}</div><div class='ds-help'>Why it matters: higher risk suggests stronger persuasion pressure.</div></div>",
            unsafe_allow_html=True,
        )
        c3.markdown(
            f"<div class='ds-card'><div class='ds-eyebrow'>Patterns Detected</div><div class='ds-kpi'>{total_patterns}</div><div class='ds-help'>Example: urgency + hidden costs can stack quickly.</div></div>",
            unsafe_allow_html=True,
        )

        fig = px.bar(
            top.sort_values("manipulation_score"),
            x="manipulation_score",
            y="domain",
            orientation="h",
            color="manipulation_score",
            color_continuous_scale=["#00d58a", "#ffbe3d", "#ff7a3d", "#ff4f6d"],
            labels={"manipulation_score": "Manipulation score", "domain": "Domain"},
        )
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)

        show = top[["domain", "vertical", "manipulation_score", "total_patterns_found", "pages_analyzed", "last_scraped"]].copy()
        show["risk_level"] = show["manipulation_score"].apply(lambda x: _risk_label(float(x))[0])
        st.dataframe(show, use_container_width=True)

elif page == "Vertical Analysis":
    st.subheader("Vertical Analysis")
    st.caption("See which industries show stronger manipulation signals.")
    sites = fetch_all_sites(DB_PATH)
    df = pd.DataFrame(sites)
    if df.empty:
        st.info("No sites available yet.")
    else:
        plot_df = df.dropna(subset=["vertical", "manipulation_score"]).copy()
        plot_df["vertical"] = plot_df["vertical"].astype(str)
        fig = px.box(plot_df, x="vertical", y="manipulation_score", points="outliers")
        fig.update_traces(marker=dict(color="#7ea4ff", opacity=0.8))
        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig, use_container_width=True)
        st.info(
            "How to read this chart: each box shows the typical score range for a vertical. "
            "Tall boxes or many outliers mean behavior is inconsistent across sites in that category."
        )

        comp_df = pd.DataFrame(get_vertical_comparison(str(DB_PATH)))
        fig2 = px.bar(
            comp_df,
            x="vertical",
            y="avg_manipulation_score",
            color="avg_manipulation_score",
            color_continuous_scale=["#00d58a", "#ffbe3d", "#ff7a3d", "#ff4f6d"],
        )
        fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig2, use_container_width=True)
        st.info(
            "How to read this chart: this compares average manipulation score by vertical. "
            "Higher bars indicate stronger average persuasion pressure."
        )

        if EVAL_SUMMARY.exists():
            summary = json.loads(EVAL_SUMMARY.read_text(encoding="utf-8"))
            chi = summary.get("chi2_vertical_dark", {})
            tv = summary.get("travel_vs_fmcg") or {}
            st.markdown(
                f"""
<div class="ds-card">
  <div class="ds-eyebrow">What this means</div>
  <div class="ds-help">A chi-square test checks whether dark-pattern prevalence differs by vertical.</div>
  <div class="ds-divider"></div>
  <div>Overall: χ²={chi.get("chi2", float("nan")):.2f}, p={chi.get("p_value", float("nan")):.2e}</div>
  <div>Travel vs FMCG subset: χ²={tv.get("chi2", float("nan")):.2f}, p={tv.get("p_value", float("nan")):.2e}</div>
</div>
""",
                unsafe_allow_html=True,
            )
        else:
            st.warning("Evaluation summary is missing. Run `python ml/models/evaluate.py`.")

        c = _conn()
        dets = pd.read_sql_query(
            """
            SELECT s.vertical, d.pattern_category, COUNT(*) c
            FROM detections d JOIN sites s ON s.id = d.site_id
            GROUP BY s.vertical, d.pattern_category
            """,
            c,
        )
        c.close()
        if not dets.empty and show_advanced:
            pivot = dets.pivot_table(index="vertical", columns="pattern_category", values="c", fill_value=0)
            fig_stack = go.Figure()
            palette = list(px.colors.qualitative.Set3) + list(px.colors.qualitative.Pastel1)
            for i, pat in enumerate(pivot.columns):
                fig_stack.add_trace(
                    go.Bar(
                        name=_human_pattern(str(pat)),
                        x=[str(v) for v in pivot.index],
                        y=[float(pivot.at[v, pat]) for v in pivot.index],
                        marker_color=palette[i % len(palette)],
                    )
                )
            fig_stack.update_layout(
                barmode="stack",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                legend_title_text="Pattern type",
            )
            st.plotly_chart(fig_stack, use_container_width=True)
            st.info(
                "Advanced view: this stacked chart shows pattern composition by vertical. "
                "Use it to see whether risk comes mostly from urgency, hidden costs, or other tactics."
            )
        elif not show_advanced:
            st.caption("Advanced stacked chart is hidden for clarity. Enable it from the sidebar if needed.")

elif page == "Data Collection & Observations":
    st.subheader("Data Collection & Observations")
    st.caption("What DarkShield gathers from websites and what has been observed so far.")
    sites = fetch_all_sites(DB_PATH)
    s_df = pd.DataFrame(sites)
    if s_df.empty:
        st.info("No collected site data yet. Run `python ml/models/evaluate.py` to populate the database.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("Sites tracked", int(s_df.shape[0]), help="Number of domains currently available in the local dataset.")
        c2.metric(
            "Total snippets flagged",
            int(s_df["total_patterns_found"].fillna(0).sum()),
            help="Total detected pattern snippets across all tracked domains.",
        )
        c3.metric(
            "Pages analyzed",
            int(s_df["pages_analyzed"].fillna(0).sum()),
            help="How many pages were analyzed to produce current scores.",
        )

        st.markdown("### What information is collected during scraping / scanning")
        st.markdown(
            """
- **Text snippet** from the page that triggered a detection
- **Pattern label** predicted by the model
- **Confidence score** of the detection
- **Domain and URL** where the snippet appeared
- **Timestamp** (`detected_at`) for timeline analysis

DarkShield is designed for transparency analysis. It does not collect user account credentials or private profile data in this workflow.
"""
        )

        with st.expander("Observed trends in current dataset"):
            top = s_df.sort_values("manipulation_score", ascending=False).head(5)
            st.markdown("- **Higher-risk domains (current snapshot):**")
            for _, row in top.iterrows():
                st.markdown(
                    f"  - `{row['domain']}`: score **{float(row.get('manipulation_score') or 0):.1f}**, "
                    f"patterns **{int(row.get('total_patterns_found') or 0)}**"
                )
            vertical_mix = (
                s_df.groupby("vertical", dropna=False)["manipulation_score"]
                .mean()
                .sort_values(ascending=False)
                .reset_index()
            )
            if not vertical_mix.empty:
                st.markdown("- **Average risk by vertical (observed):**")
                for _, row in vertical_mix.iterrows():
                    st.markdown(f"  - `{row['vertical']}`: average score **{float(row['manipulation_score']):.1f}**")

elif page == "Site Deep Dive":
    st.subheader("Site Deep Dive")
    st.caption("Inspect one site in detail: pattern mix, trend, and raw snippets.")
    sites = fetch_all_sites(DB_PATH)
    if not sites:
        st.info("No sites available yet.")
    else:
        domain = st.selectbox("Choose a site", [s["domain"] for s in sites])
        dets = fetch_detections_for_domain(DB_PATH, domain)
        ddf = pd.DataFrame(dets)
        if ddf.empty:
            st.warning("No detections stored for this domain.")
        else:
            counts = ddf["pattern_category"].value_counts()
            riskish = float(ddf.get("confidence", pd.Series(dtype=float)).fillna(0).mean() * 100)
            c1, c2, c3 = st.columns(3)
            c1.metric("Patterns detected", int(len(ddf)), help="What this means: number of flagged snippets for this domain.")
            c2.metric("Pattern types", int(counts.shape[0]), help="Why it matters: more types suggests more varied persuasion tactics.")
            c3.metric("Avg confidence", f"{riskish:.1f}%", help="Example: 90% indicates the model was very certain for many snippets.")

            pie = go.Figure(data=[go.Pie(labels=[_human_pattern(x) for x in counts.index], values=counts.values, hole=0.5)])
            pie.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(pie, use_container_width=True)
            st.info(
                "How to read this chart: larger donut slices mean that pattern appears more often on this site."
            )

            tdf = ddf.copy()
            tdf["detected_at"] = pd.to_datetime(tdf["detected_at"], errors="coerce")
            daily = tdf.groupby(tdf["detected_at"].dt.date).size().reset_index(name="count")
            if not daily.empty:
                fig2 = px.line(daily, x="detected_at", y="count", markers=True)
                fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig2, use_container_width=True)
                st.info(
                    "How to read this chart: spikes indicate days when more manipulative snippets were detected."
                )
            else:
                st.caption("Not enough timestamped rows to show a daily trend chart.")

            hist = get_score_history(str(DB_PATH), domain)
            if hist:
                hdf = pd.DataFrame(hist)
                hdf["snapshot_date"] = pd.to_datetime(hdf["snapshot_date"], errors="coerce")
                if len(hdf) >= 2:
                    fig_ts = go.Figure()
                    fig_ts.add_trace(
                        go.Scatter(
                            x=hdf["snapshot_date"],
                            y=hdf["manipulation_score"],
                            mode="lines+markers",
                            name="Manipulation score",
                            line=dict(color="#7ea4ff"),
                        )
                    )
                    fig_ts.update_layout(
                        title="Weekly score trend",
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig_ts, use_container_width=True)
                    st.info(
                        "How to read this chart: rising line means persuasion pressure is increasing over time for this domain."
                    )
                else:
                    st.caption("Not enough history points to show a meaningful weekly trend.")

            with st.expander("Detailed snippets"):
                ddf_show = ddf[["pattern_category", "confidence", "text_snippet", "url", "detected_at"]].copy()
                ddf_show["pattern_category"] = ddf_show["pattern_category"].astype(str).map(_human_pattern)
                st.dataframe(ddf_show.head(200), use_container_width=True)

elif page == "Full Pattern Report":
    st.subheader("Pattern Explanation Layer")
    st.caption("Every pattern includes simple meaning, impact, and an example.")
    g1, g2 = st.tabs(["Pattern Encyclopedia", "All detections by site"])
    with g1:
        labels = sorted(k for k in EXPLANATIONS if k != "none")
        for lab in labels:
            with st.expander(f"{_human_pattern(lab)} ({lab})"):
                tags = get_compliance_tags(lab) or {}
                st.markdown(f"- **What this means:** {EXPLANATIONS.get(lab, 'No explanation available.')}")
                st.markdown("- **Why it matters:** This pattern can push users toward decisions they may not fully intend.")
                st.markdown(f"- **Example:** {PATTERN_EXAMPLES.get(lab, 'Example not available.')}")
                if tags:
                    st.markdown("- **Regulatory context (educational):**")
                    for key in ("CCPA_2023", "EU_Dark_Patterns", "FTC_Act", "India_IT_Rules_2021"):
                        if key in tags and isinstance(tags[key], str):
                            st.markdown(f"  - {key.replace('_', ' ')}: {tags[key]}")
    with g2:
        sites = fetch_all_sites(DB_PATH)
        if not sites:
            st.info("No site data yet.")
        else:
            by_dom = {str(s["domain"]): s for s in sites}
            domain = st.selectbox("Choose site", sorted(by_dom.keys()), key="full_report_domain")
            site_row = by_dom.get(domain, {})
            dets = fetch_detections_for_domain(DB_PATH, domain)
            if not dets:
                st.warning(f"No detections stored for `{domain}`.")
            else:
                ddf = pd.DataFrame(dets)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Manipulation score", f"{float(site_row.get('manipulation_score') or 0):.1f}")
                c2.metric("Detected snippets", len(ddf))
                c3.metric("Vertical", str(site_row.get("vertical") or "—"))
                c4.metric("Pages analyzed", int(site_row.get("pages_analyzed") or 0))
                for pat in sorted(ddf["pattern_category"].astype(str).unique()):
                    sub = ddf[ddf["pattern_category"] == pat].copy()
                    with st.expander(f"{_human_pattern(pat)} · {len(sub)} snippet(s)"):
                        st.markdown(f"- **What this means:** {EXPLANATIONS.get(pat, 'No explanation available.')}")
                        st.markdown("- **Why it matters:** Repeated exposure can increase user pressure and reduce informed consent.")
                        st.markdown(f"- **Example:** {PATTERN_EXAMPLES.get(pat, 'Example not available.')}")
                        sub["detected_at"] = pd.to_datetime(sub["detected_at"], errors="coerce")
                        sub = sub.sort_values("detected_at", ascending=False)
                        for i, (_, row) in enumerate(sub.iterrows(), start=1):
                            st.markdown(f"**Snippet {i}** · confidence `{row.get('confidence')}`")
                            if row.get("url"):
                                st.caption(str(row.get("url"))[:200])
                            st.text_area(
                                "Flagged copy",
                                value=str(row.get("text_snippet") or "")[:4000],
                                key=f"det_{domain}_{pat}_{i}",
                                height=96,
                                disabled=True,
                            )

elif page == "A/B Test Detection":
    st.subheader("A/B Testing Signal Checker")
    st.caption("This heuristic compares multiple fetches of the same domain to detect message variability.")
    st.markdown(
        """
- **What this means:** DarkShield rotates user agents and compares detected pattern counts.
- **Why it matters:** Large variance may indicate personalized persuasion or experimentation.
- **Example:** Session A shows countdown urgency, Session B does not.
"""
    )
    dom = st.text_input("Domain", "flipkart.com")
    if st.button("Run comparison"):
        with st.spinner("Running multi-session fetch..."):
            try:
                report = detect_ab_testing(dom.strip() or "flipkart.com", n_sessions=10)
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
                report = None
        if report:
            st.success(report.get("conclusion", "Report generated."))
            st.json({k: v for k, v in report.items() if k != "sessions"})
            with st.expander("Session-level details"):
                st.json(report.get("sessions", [])[:4])

else:
    st.subheader("Platform Statistics")
    st.caption("High-level health and progress of your transparency dataset.")
    s = aggregate_stats(str(DB_PATH))
    c1, c2, c3 = st.columns(3)
    c1.metric("Total sites", s["total_sites"], help="What this means: domains currently tracked in SQLite.")
    c2.metric("Total patterns detected", s["total_patterns_detected"], help="Why it matters: broader evidence base for risk analysis.")
    c3.metric("User reports", s["total_user_reports"], help="Example: false-positive feedback submitted from extension popup.")
    st.markdown(f"- **Most common pattern:** {_human_pattern(s['most_common_pattern'])}")
    st.markdown(f"- **Highest-risk domain:** `{s['worst_offender_domain']}` ({s['worst_offender_score']:.2f})")

    if EVAL_SUMMARY.exists():
        summary = json.loads(EVAL_SUMMARY.read_text(encoding="utf-8"))
        st.markdown(
            f"- **Latest model evaluation:** {summary.get('evaluated_at')}  \n"
            f"- **Macro F1 (merged confirm-shaming pass):** {summary.get('macro_f1_merged_pred')}"
        )
    else:
        st.info("No evaluation summary found yet.")

st.markdown("---")
st.markdown("### What should you do next?")
st.markdown(
    """
1. Open **Site Deep Dive** for domains that rank high in the leaderboard.
2. Validate suspicious snippets using **Full Pattern Report**.
3. Re-run `ml/models/evaluate.py` after model updates to refresh insights.
4. Track weekly movement using `python -m ml.database.temporal_tracker`.
"""
)
