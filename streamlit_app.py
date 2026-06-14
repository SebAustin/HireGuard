"""HireGuard — interactive showcase demo.

A self-contained Streamlit app (no band-sdk, no secrets) that demonstrates the
four-agent hiring-compliance audit: pick a sample packet, watch the agents hand
off in the Band room, and read the cited audit memo. Reads the real ruleset and
sample packets from the repo; the audit results are the verdicts the live
pipeline produces.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
RULESET = json.loads((ROOT / "hireguard/rules/ruleset.json").read_text())
SAMPLES = {
    "acme_se_role": json.loads((ROOT / "hireguard/samples/acme_se_role.json").read_text()),
    "northwind_pm_role": json.loads((ROOT / "hireguard/samples/northwind_pm_role.json").read_text()),
}

SEV = {
    "Critical": "#FB6B6B", "Risk": "#F7B25C", "Gap": "#5FA8FB",
    "Suggestion": "#4ADE80", "Clear": "#4ADE80",
}
AGENT_CLR = {"@Intake": "#5EEAD4", "@PolicyAgent": "#8B93F8", "@RiskScorer": "#E8C16B", "@Counsel": "#4ADE80"}

# --- the verdicts the live pipeline produces for each sample ------------------
DEMO = {
    "acme_se_role": {
        "verdict": "HIGH", "verdict_clr": "#FB6B6B",
        "room": [
            ("@Intake", "facts.md ready — packet extracted (Acme Robotics, San Francisco)."),
            ("@PolicyAgent", "6 candidate findings posted. → @RiskScorer"),
            ("@RiskScorer", "scored every finding via the AI/ML API — overall verdict HIGH. → @Counsel"),
            ("@Counsel", "@PolicyAgent re-examine a thin Critical before I sign…"),
            ("@Counsel", "audit complete — memo written, awaiting human sign-off."),
        ],
        "findings": [
            {"id": "PAYHIST-SALARY-BAN", "cat": "Critical", "score": 86,
             "evidence": "“Apply now — tell us your current salary so we can calibrate the offer.”",
             "citation": "CA Labor Code §432.3(b); NY Labor Law §194-a (salary-history bans)",
             "why": "Direct salary-history inquiry; banned in the employer's jurisdiction."},
            {"id": "PAYTRANS-CA-SB1162", "cat": "Critical", "score": 88,
             "evidence": "Posted salary range: not provided (CA employer, 240 employees).",
             "citation": "CA Labor Code §432.3 (SB 1162, eff. 2023)",
             "why": "CA employers with 15+ staff must post a pay scale; clear exposure."},
            {"id": "EEOC-ADEA-AGE", "cat": "Risk", "score": 62,
             "evidence": "“young, energetic … recent grad … digital native”",
             "citation": "Age Discrimination in Employment Act, 29 U.S.C. §623",
             "why": "Age-proxy language signals bias against older applicants."},
            {"id": "EEOC-NATL-ORIGIN", "cat": "Risk", "score": 55,
             "evidence": "“must be a native English speaker”",
             "citation": "Title VII; 29 C.F.R. §1606.6",
             "why": "Native-speaker requirement is national-origin overreach."},
            {"id": "EEOC-ADA-DISABILITY", "cat": "Risk", "score": 48,
             "evidence": "“must be able to lift 40 lbs” — no accommodation noted",
             "citation": "ADA, 42 U.S.C. §12112; 29 C.F.R. §1630",
             "why": "Physical requirement stated without reasonable-accommodation language."},
            {"id": "EEOC-DISPARATE-SUBJECTIVE", "cat": "Gap", "score": 34,
             "evidence": "“Culture fit” scorecard criterion, unanchored.",
             "citation": "Title VII disparate-impact doctrine, 42 U.S.C. §2000e-2(k)",
             "why": "Subjective, unanchored criteria invite disparate-impact claims."},
        ],
    },
    "northwind_pm_role": {
        "verdict": "LOW", "verdict_clr": "#4ADE80",
        "room": [
            ("@Intake", "facts.md ready — packet extracted (Northwind Analytics, Denver)."),
            ("@PolicyAgent", "0 candidate findings — posting looks clean. → @RiskScorer"),
            ("@RiskScorer", "nothing to score — overall verdict LOW. → @Counsel"),
            ("@Counsel", "audit complete — no Critical issues identified. Awaiting sign-off."),
        ],
        "findings": [
            {"id": "PAYTRANS-CO-EPEWA", "cat": "Suggestion", "score": 8,
             "evidence": "Salary range $130k–$165k and benefits disclosed in the listing.",
             "citation": "CO Equal Pay for Equal Work Act, C.R.S. §8-5-201",
             "why": "Compliant — pay range and benefits are disclosed as Colorado requires."},
        ],
    },
}

# ------------------------------------------------------------------------------
st.set_page_config(page_title="HireGuard — multi-agent compliance auditor",
                   page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.block-container{padding-top:2.2rem;max-width:1180px;}
.hg-eyebrow{color:#5EEAD4;font-weight:600;letter-spacing:.18em;text-transform:uppercase;font-size:.8rem;}
.hg-card{background:#141B30;border:1px solid rgba(148,163,184,.18);border-radius:14px;padding:18px 20px;height:100%;}
.hg-card h4{margin:0 0 .4rem 0;font-size:1.05rem;}
.hg-fw{font-family:ui-monospace,monospace;font-size:.7rem;color:#9AA8BE;border:1px solid rgba(148,163,184,.25);border-radius:6px;padding:2px 7px;}
.hg-badge{display:inline-block;font-size:.72rem;font-weight:600;letter-spacing:.05em;text-transform:uppercase;
  padding:4px 11px;border-radius:7px;}
.hg-rule{font-family:ui-monospace,monospace;font-weight:600;}
.hg-bubble{background:#0E1424;border:1px solid rgba(148,163,184,.18);border-radius:12px;padding:11px 15px;margin-bottom:9px;}
.hg-find{background:#101728;border:1px solid rgba(148,163,184,.16);border-radius:12px;padding:14px 16px;margin-bottom:11px;}
.hg-track{height:7px;border-radius:5px;background:rgba(148,163,184,.18);margin-top:9px;overflow:hidden;}
.hg-fill{height:100%;border-radius:5px;}
.hg-verdict{font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:2.2rem;letter-spacing:-1px;}
small.hg-mut{color:#9AA8BE;}
</style>
""", unsafe_allow_html=True)


def badge(cat: str) -> str:
    c = SEV.get(cat, "#9AA8BE")
    return f'<span class="hg-badge" style="color:{c};background:{c}22;border:1px solid {c}55;">{cat}</span>'


def render_findings(sample: str):
    d = DEMO[sample]
    crit = sum(1 for f in d["findings"] if f["cat"] == "Critical")
    risk = sum(1 for f in d["findings"] if f["cat"] == "Risk")
    gap = sum(1 for f in d["findings"] if f["cat"] == "Gap")
    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(
            f'<div class="hg-card"><small class="hg-mut">AUDIT VERDICT</small><br>'
            f'<span class="hg-verdict" style="color:{d["verdict_clr"]}">{d["verdict"]}</span><br>'
            f'<small class="hg-mut">{len(d["findings"])} cited findings · '
            f'{crit} Critical · {risk} Risk · {gap} Gap</small></div>',
            unsafe_allow_html=True)
    with c2:
        st.markdown('<small class="hg-mut">audit.md → grouped by severity, each with a rule, '
                    'quoted evidence, a citation, and an AI/ML API exposure score.</small>',
                    unsafe_allow_html=True)
    st.write("")
    for f in d["findings"]:
        c = SEV.get(f["cat"], "#9AA8BE")
        st.markdown(
            f'<div class="hg-find">'
            f'{badge(f["cat"])} &nbsp; <span class="hg-rule">{f["id"]}</span>'
            f'<div style="margin-top:8px">{f["evidence"]}</div>'
            f'<div style="margin-top:6px"><small class="hg-mut">📑 {f["citation"]}</small></div>'
            f'<div style="margin-top:6px"><small class="hg-mut">{f["why"]}</small></div>'
            f'<div style="display:flex;align-items:center;gap:10px;margin-top:6px">'
            f'<small class="hg-mut" style="white-space:nowrap">AI/ML exposure</small>'
            f'<div class="hg-track" style="flex:1"><div class="hg-fill" style="width:{f["score"]}%;background:{c}"></div></div>'
            f'<small class="hg-mut" style="white-space:nowrap">{f["score"]}/100</small></div>'
            f'</div>', unsafe_allow_html=True)
    st.markdown('<small class="hg-mut">— Human sign-off required: ☐ Reviewed by ________  Date ____</small>',
                unsafe_allow_html=True)


# --- header -------------------------------------------------------------------
st.markdown('<span class="hg-eyebrow">Multi-agent hiring-compliance auditor</span>', unsafe_allow_html=True)
st.title("🛡️ HireGuard")
st.markdown("Four specialized AI agents collaborate inside a **Band** room to audit hiring "
            "artifacts for **EEOC** and **pay-transparency** risk — then hand off, score via the "
            "**AI/ML API**, and write a defensible, cited audit memo.")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Agents", "4")
m2.metric("Frameworks", "2", help="LangGraph + CrewAI")
m3.metric("Compliance rules", str(len(RULESET["rules"])))
m4.metric("AI/ML API", "load-bearing", help="No risk score without it")

tab_demo, tab_over, tab_rules, tab_video = st.tabs(
    ["▶ Live audit demo", "Overview", "The ruleset", "Watch the film"])

# --- live demo ----------------------------------------------------------------
with tab_demo:
    st.subheader("Run a compliance audit")
    label = {"acme_se_role": "Acme Robotics — Software Engineer (planted violations)",
             "northwind_pm_role": "Northwind Analytics — Product Manager (clean posting)"}
    sample = st.radio("Choose a hiring packet", list(SAMPLES), format_func=lambda k: label[k],
                      horizontal=True)
    pkt = SAMPLES[sample]
    colL, colR = st.columns(2)
    with colL:
        st.markdown(f"**{pkt['company']}** · {pkt['company_size']} employees · {pkt['primary_work_location']}")
        cb = pkt["comp_band"]
        rng = cb.get("posted_range_in_listing")
        st.markdown(f"Posted salary range: **{'$%s–$%s' % (rng['min'], rng['max']) if rng else 'not provided'}**")
    with colR:
        st.markdown("**Job posting (excerpt)**")
        st.caption(pkt["job_posting"][:320] + "…")

    if "ran" not in st.session_state:
        st.session_state.ran = {}

    if st.button("⚖️  Run the 4-agent audit", type="primary"):
        with st.status("Agents collaborating in the Band room…", expanded=True) as status:
            for who, msg in DEMO[sample]["room"]:
                clr = AGENT_CLR.get(who, "#9AA8BE")
                st.markdown(f'<div class="hg-bubble"><b style="color:{clr}">{who}</b> &nbsp;{msg}</div>',
                            unsafe_allow_html=True)
                time.sleep(0.9)
            status.update(label="Audit complete — memo written to audit.md", state="complete")
        st.session_state.ran[sample] = True

    if st.session_state.ran.get(sample):
        st.divider()
        render_findings(sample)

# --- overview -----------------------------------------------------------------
with tab_over:
    if (ROOT / "submission/cover.png").exists():
        st.image(str(ROOT / "submission/cover.png"), use_container_width=True)
    st.markdown("### How it works")
    if (ROOT / "docs/architecture.png").exists():
        st.image(str(ROOT / "docs/architecture.png"), use_container_width=True)
    agents = [
        ("@Intake", "LangGraph", "Reads the raw packet, extracts structured facts → facts.md"),
        ("@PolicyAgent", "LangGraph", "Applies the ruleset, cites candidate violations"),
        ("@RiskScorer", "CrewAI", "Scores legal exposure 0–100 per finding via the AI/ML API → risk.md"),
        ("@Counsel", "CrewAI", "Validates, de-dupes, bounces thin Criticals, writes audit.md"),
    ]
    cols = st.columns(4)
    for col, (nm, fw, role) in zip(cols, agents):
        col.markdown(
            f'<div class="hg-card"><h4 style="color:{AGENT_CLR[nm]}">{nm}</h4>'
            f'<span class="hg-fw">{fw}</span><p style="margin-top:.6rem">{role}</p></div>',
            unsafe_allow_html=True)
    st.write("")
    st.markdown("**Chat is for coordination; files are for content.** Agents hand off via "
                "`@mentions`; the audit content lives in shared workspace notes. The **AI/ML API "
                "is load-bearing** — a finding has no risk score until that call returns.")
    st.link_button("View the source on GitHub", "https://github.com/SebAustin/HireGuard")

# --- ruleset ------------------------------------------------------------------
with tab_rules:
    st.subheader(f"{len(RULESET['rules'])} real, citeable rules")
    st.caption("EEOC anti-discrimination law + state pay-transparency statutes. "
               "Each finding the agents raise must cite one of these rule IDs.")
    for r in RULESET["rules"]:
        c = SEV.get(r.get("category_default", "Gap"), "#9AA8BE")
        with st.expander(f"{r['rule_id']} — {r['title']}"):
            st.markdown(f"{badge(r.get('category_default','Gap'))} &nbsp; "
                        f"**Jurisdiction:** {r['jurisdiction']}", unsafe_allow_html=True)
            st.markdown(f"**Citation:** {r['citation']}")
            hints = r.get("detection_hints", [])
            if hints:
                st.markdown("**Detection hints:** " + ", ".join(f"`{h}`" for h in hints[:8]))

# --- video --------------------------------------------------------------------
with tab_video:
    st.subheader("The 45-second narrated explainer")
    vid = ROOT / "submission/explainer_narrated.mp4"
    if vid.exists():
        st.video(str(vid))
    st.caption("Also in the repo: a slide deck (submission/deck.pdf) and the cover image.")
    st.link_button("⭐ Star / view on GitHub", "https://github.com/SebAustin/HireGuard")

st.divider()
st.caption("HireGuard · Band of Agents Hackathon · Track 3 (Regulated & High-Stakes) · "
           "Best Use of the AI/ML API. This showcase runs offline; the live pipeline runs the "
           "four agents on Band.")
