"""
Streamlit transparency dashboard for DarkShield SQLite database + evaluation artifacts.
"""

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
from ml.database.transparency_db import aggregate_stats, fetch_all_sites, fetch_detections_for_domain, get_score_history
from ml.database.site_scorer import get_vertical_comparison

DB_PATH = Path(_ROOT / "data" / "darkshield.db")
EVAL_SUMMARY = _ROOT / "ml" / "models" / "saved" / "eval_results" / "summary.json"


def _conn():
    return sqlite3.connect(DB_PATH)


st.set_page_config(page_title="DarkShield Transparency", layout="wide")
st.markdown(
    """
<style>
  .stApp { background-color: #0d1117; color: #e6edf3; }
  h1, h2, h3 { font-family: "Courier New", ui-monospace, monospace; }
  div[data-testid="stMetricValue"] { font-family: "Courier New", ui-monospace, monospace; }
</style>
""",
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Navigate",
    [
        "Leaderboard",
        "Vertical Analysis",
        "Site Deep Dive",
        "Full pattern report",
        "A/B Test Detection",
        "Statistics",
    ],
)

st.sidebar.caption("DarkShield local transparency DB viewer")

if page == "Leaderboard":
    st.title("DarkShield Transparency Database")
    vertical = st.selectbox("Vertical filter", ["all", "travel", "fmcg", "fashion", "electronics", "food_delivery"])

    sites = fetch_all_sites(DB_PATH)
    df = pd.DataFrame(sites)
    if not df.empty and vertical != "all":
        df = df[df["vertical"] == vertical]

    st.subheader("Top 20 sites by manipulation score")
    top = df.sort_values("manipulation_score", ascending=False).head(20) if not df.empty else df
    if top.empty:
        st.info("No sites in DB yet. Run `python ml/models/evaluate.py` after training.")
    else:
        fig = px.bar(
            top,
            x="manipulation_score",
            y="domain",
            orientation="h",
            color="manipulation_score",
            color_continuous_scale=["#00ff88", "#ffb800", "#ff6b35", "#ff1744"],
        )
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
        st.plotly_chart(fig, use_container_width=True)

        st.dataframe(
            top[
                [
                    "domain",
                    "manipulation_score",
                    "total_patterns_found",
                    "pages_analyzed",
                    "last_scraped",
                ]
            ],
            use_container_width=True,
        )

elif page == "Vertical Analysis":
    st.title("Vertical Analysis")
    sites = fetch_all_sites(DB_PATH)
    df = pd.DataFrame(sites)
    if df.empty:
        st.info("No sites in DB yet.")
    else:
        plot_df = df.dropna(subset=["vertical", "manipulation_score"]).copy()
        plot_df["vertical"] = plot_df["vertical"].astype(str)
        # Do not set color=vertical when x=vertical — Plotly can mis-handle category
        # iteration and raise KeyError on some pandas/plotly versions.
        fig = px.box(
            plot_df,
            x="vertical",
            y="manipulation_score",
            points="outliers",
        )
        fig.update_traces(marker=dict(color="#00ff88", opacity=0.85))
        fig.update_layout(template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
        st.plotly_chart(fig, use_container_width=True)

        comp = get_vertical_comparison(str(DB_PATH))
        comp_df = pd.DataFrame(comp)
        fig2 = px.bar(comp_df, x="vertical", y="avg_manipulation_score", color="avg_manipulation_score")
        fig2.update_layout(template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
        st.plotly_chart(fig2, use_container_width=True)

        if EVAL_SUMMARY.exists():
            summary = json.loads(EVAL_SUMMARY.read_text(encoding="utf-8"))
            chi = summary.get("chi2_vertical_dark", {})
            p = chi.get("p_value")
            tv = summary.get("travel_vs_fmcg") or {}
            st.success(
                "Chi-square (vertical × dark-pattern prevalence): "
                f"χ²={chi.get('chi2'):.2f}, p={p:.2e}. "
                f"Travel vs FMCG subset: χ²={tv.get('chi2', float('nan')):.2f}, p={tv.get('p_value', float('nan')):.2e}."
            )
        else:
            st.warning("Run evaluation to generate chi-square summary JSON.")

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
        if not dets.empty:
            pivot = dets.pivot_table(
                index="vertical",
                columns="pattern_category",
                values="c",
                fill_value=0,
            )
            # Avoid px.bar(..., color="pattern"): Plotly Express can KeyError on
            # underscore pattern names (e.g. bait_and_switch) with some versions.
            verticals = [str(v) for v in pivot.index.tolist()]
            patterns = [str(p) for p in pivot.columns.tolist()]
            palette = list(px.colors.qualitative.Set3) + list(px.colors.qualitative.Pastel1)
            fig_stack = go.Figure()
            for i, pat in enumerate(patterns):
                ys = [float(pivot.at[v, pat]) for v in pivot.index]
                fig_stack.add_trace(
                    go.Bar(
                        name=pat.replace("_", " "),
                        x=verticals,
                        y=ys,
                        marker_color=palette[i % len(palette)],
                    )
                )
            fig_stack.update_layout(
                barmode="stack",
                template="plotly_dark",
                paper_bgcolor="#0d1117",
                plot_bgcolor="#0d1117",
                legend_title_text="Pattern",
            )
            st.plotly_chart(fig_stack, use_container_width=True)

elif page == "Site Deep Dive":
    st.title("Site Deep Dive")
    sites = fetch_all_sites(DB_PATH)
    if not sites:
        st.info("No sites in DB yet.")
    else:
        domain = st.selectbox("Select site", [s["domain"] for s in sites])
        dets = fetch_detections_for_domain(DB_PATH, domain)
        ddf = pd.DataFrame(dets)
        if ddf.empty:
            st.warning("No detections stored for this domain.")
        else:
            counts = ddf["pattern_category"].value_counts().reset_index()
            counts.columns = ["pattern_category", "count"]
            fig = go.Figure(
                data=[go.Pie(labels=counts["pattern_category"], values=counts["count"], hole=0.55)]
            )
            fig.update_layout(template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
            st.plotly_chart(fig, use_container_width=True)

            tdf = ddf.copy()
            tdf["detected_at"] = pd.to_datetime(tdf["detected_at"], errors="coerce")
            daily = tdf.groupby(tdf["detected_at"].dt.date).size().reset_index(name="count")
            fig2 = px.line(daily, x="detected_at", y="count", markers=True)
            fig2.update_layout(template="plotly_dark", paper_bgcolor="#0d1117", plot_bgcolor="#0d1117")
            st.plotly_chart(fig2, use_container_width=True)

            hist = get_score_history(str(DB_PATH), domain)
            if hist:
                hdf = pd.DataFrame(hist)
                hdf["snapshot_date"] = pd.to_datetime(hdf["snapshot_date"], errors="coerce")
                sale_windows = [
                    ("Diwali season", "2026-10-15", "2026-11-08"),
                    ("Big Billion Day window", "2026-09-25", "2026-10-15"),
                    ("End of Season Sale", "2026-06-01", "2026-07-15"),
                ]
                fig_ts = go.Figure()
                fig_ts.add_trace(
                    go.Scatter(
                        x=hdf["snapshot_date"],
                        y=hdf["manipulation_score"],
                        mode="lines+markers",
                        name="manipulation_score",
                        line=dict(color="#00ff88"),
                    )
                )
                for name, s, e in sale_windows:
                    fig_ts.add_vrect(
                        x0=s,
                        x1=e,
                        fillcolor="rgba(0, 255, 136, 0.07)",
                        layer="below",
                        line_width=0,
                        annotation_text=name,
                        annotation_position="top left",
                    )
                fig_ts.update_layout(
                    title="Manipulation score over time (weekly snapshots)",
                    template="plotly_dark",
                    paper_bgcolor="#0d1117",
                    plot_bgcolor="#0d1117",
                )
                st.plotly_chart(fig_ts, use_container_width=True)

                for i in range(1, len(hdf)):
                    prev = float(hdf.iloc[i - 1]["manipulation_score"])
                    cur = float(hdf.iloc[i]["manipulation_score"])
                    delta = cur - prev
                    dt = hdf.iloc[i]["snapshot_date"]
                    if delta > 15 and pd.notna(dt):
                        for sale_name, s, e in sale_windows:
                            sdt = pd.to_datetime(s)
                            edt = pd.to_datetime(e)
                            if sdt <= dt <= edt + pd.Timedelta(days=14):
                                st.success(
                                    f"**Insight:** `{domain}` manipulation score rose by **{delta:+.1f}** points within two weeks of **{sale_name}** — "
                                    "often coincident with elevated `fake_urgency` and promotional density on Indian marketplaces."
                                )
                                break
            else:
                st.caption("No `score_history` rows yet. Run `python -m ml.database.temporal_tracker` to append snapshots.")

            st.dataframe(
                ddf[["pattern_category", "confidence", "text_snippet", "url", "detected_at"]].head(200),
                use_container_width=True,
            )

elif page == "Full pattern report":
    st.title("Full pattern report")
    st.caption(
        "Plain-language definitions, regulatory context (educational only), and every stored detection "
        "with the actual on-page text the model flagged."
    )
    g1, g2 = st.tabs(["Pattern encyclopedia", "All detections by site"])

    with g1:
        st.subheader("What each label means")
        labels = sorted(k for k in EXPLANATIONS if k != "none")
        for lab in labels:
            human = lab.replace("_", " ").title()
            expl = EXPLANATIONS[lab]
            tags = get_compliance_tags(lab)
            sev = tags.get("severity", "—") if tags else "—"
            with st.expander(f"{human} · model label: `{lab}` · severity: **{sev}**"):
                st.markdown(f"**In simple terms:** {expl}")
                if not tags:
                    st.caption("No regulatory mapping for this label.")
                    continue
                st.markdown("**Why regulators care (illustrative, not legal advice):**")
                for key in ("CCPA_2023", "EU_Dark_Patterns", "FTC_Act", "India_IT_Rules_2021"):
                    if key in tags and isinstance(tags[key], str):
                        st.markdown(f"- **{key.replace('_', ' ')}:** {tags[key]}")
                cases = tags.get("enforcement_cases") or []
                if cases:
                    st.markdown("**Related enforcement / guidance themes:**")
                    for c in cases[:5]:
                        st.markdown(f"- {c}")

    with g2:
        sites = fetch_all_sites(DB_PATH)
        if not sites:
            st.info("No sites in the database yet. Run `python ml/models/evaluate.py` after training.")
        else:
            by_dom = {str(s["domain"]): s for s in sites}
            domain = st.selectbox("Choose a site", sorted(by_dom.keys()), key="full_report_domain")
            site_row = by_dom.get(domain, {})
            dets = fetch_detections_for_domain(DB_PATH, domain)
            if not dets:
                st.warning(f"No detections stored for `{domain}`.")
            else:
                ddf = pd.DataFrame(dets)
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Manipulation score", f"{float(site_row.get('manipulation_score') or 0):.1f}")
                c2.metric("Patterns (rows)", len(ddf))
                c3.metric("Vertical", str(site_row.get("vertical") or "—"))
                c4.metric("Pages analyzed", int(site_row.get("pages_analyzed") or 0))
                st.divider()
                for pat in sorted(ddf["pattern_category"].astype(str).unique()):
                    sub = ddf[ddf["pattern_category"] == pat]
                    expl = EXPLANATIONS.get(pat, "No built-in description.")
                    tags = get_compliance_tags(pat)
                    sev = tags.get("severity", "—") if tags else "—"
                    with st.expander(f"**{pat.replace('_', ' ')}** — {len(sub)} snippet(s) · severity {sev}"):
                        st.markdown(f"**What this pattern is:** {expl}")
                        if tags:
                            ftca = tags.get("FTC_Act")
                            if ftca:
                                st.caption(f"FTC framing (educational): {ftca}")
                        st.markdown("**Flagged text from this site** (newest first):")
                        sub_show = sub.copy()
                        sub_show["detected_at"] = pd.to_datetime(sub_show["detected_at"], errors="coerce")
                        sub_show = sub_show.sort_values("detected_at", ascending=False)
                        for i, (_, row) in enumerate(sub_show.iterrows()):
                            conf = row.get("confidence")
                            url = row.get("url") or ""
                            ts = row.get("detected_at") or ""
                            txt = str(row.get("text_snippet") or "").strip()
                            st.markdown(f"**#{i + 1}** · confidence `{conf}` · `{ts}`")
                            if url:
                                st.caption(url[:200])
                            h = int(min(200, max(72, 36 + len(txt) // 6)))
                            st.text_area(
                                "UI copy",
                                value=txt[:4000],
                                height=h,
                                key=f"det_{domain}_{pat}_{i}",
                                disabled=True,
                            )

elif page == "A/B Test Detection":
    st.title("A/B test detection (heuristic)")
    st.caption(
        "Fetches the same homepage with rotating user agents and compares rule-based pattern hits. "
        "High variance suggests inconsistent HTML or possible experiments — not definitive proof of A/B tests."
    )
    dom = st.text_input("Domain", "flipkart.com")
    if st.button("Run multi-session comparison"):
        with st.spinner("Fetching…"):
            try:
                report = detect_ab_testing(dom.strip() or "flipkart.com", n_sessions=10)
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))
                report = None
        if report:
            st.subheader("Summary")
            st.write(report.get("conclusion", ""))
            st.json({k: v for k, v in report.items() if k != "sessions"})
            with st.expander("Raw sessions (truncated)"):
                st.json(report.get("sessions", [])[:4])

else:
    st.title("Statistics")
    s = aggregate_stats(str(DB_PATH))
    c1, c2, c3 = st.columns(3)
    c1.metric("Total sites", s["total_sites"])
    c2.metric("Total patterns detected", s["total_patterns_detected"])
    c3.metric("User reports", s["total_user_reports"])
    st.write(f"Most common pattern: **{s['most_common_pattern']}**")
    st.write(f"Worst offender: **{s['worst_offender_domain']}** ({s['worst_offender_score']:.2f})")

    if EVAL_SUMMARY.exists():
        summary = json.loads(EVAL_SUMMARY.read_text(encoding="utf-8"))
        st.write(
            f"Last evaluation: **{summary.get('evaluated_at')}** · "
            f"Macro F1 (merged confirm-shaming pass): **{summary.get('macro_f1_merged_pred')}**"
        )
    else:
        st.info("No evaluation summary found.")

    st.caption("Screenshot placeholders: add `docs/screenshots/` in your fork for UI captures.")
