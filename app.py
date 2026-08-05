"""SAP Extensibility Decision Engine.

Decides how a change should be built on S/4HANA, and shows its working.
"""

import json
import os
import streamlit as st

from engine import llm, retrieval, rules as rules_mod, pipeline
from engine.schemas import TIER_LABELS

DATA = os.path.join(os.path.dirname(__file__), "data")

st.set_page_config(page_title="SAP Extensibility Decision Engine", layout="wide")

# ---------------------------------------------------------------- sidebar

st.sidebar.title("Setup")

sidebar_key = st.sidebar.text_input("Gemini API key", type="password")
api_key = llm.get_api_key(st.secrets if hasattr(st, "secrets") else None, sidebar_key)

if not api_key:
    st.sidebar.error("No API key found.")
    st.title("SAP Extensibility Decision Engine")
    st.info(
        "Add a Gemini API key to begin. Either paste one in the sidebar, or set "
        "`GEMINI_API_KEY` in Streamlit secrets."
    )
    st.stop()

llm.configure(api_key)


@st.cache_resource(show_spinner="Embedding the catalogue…")
def load_everything():
    catalogue = retrieval.load_catalogue(os.path.join(DATA, "mm_catalogue.json"))
    matrix = retrieval.build_index(catalogue)
    rules_cfg = rules_mod.load_rules(os.path.join(DATA, "tier_rules.yaml"))
    with open(os.path.join(DATA, "gold_requirements.json")) as f:
        gold = json.load(f)["requirements"]
    return catalogue, matrix, rules_cfg, gold


catalogue, matrix, rules_cfg, gold = load_everything()

st.sidebar.caption(
    f"{len(catalogue['entries'])} catalogue entries · rules v{rules_cfg['version']} · "
    f"module {catalogue['module_scope'].split('—')[0].strip()}"
)

low_conf = [e for e in catalogue["entries"] if e.get("confidence") == "low"]
if low_conf:
    st.sidebar.warning(
        f"{len(low_conf)} catalogue entr{'y' if len(low_conf)==1 else 'ies'} marked "
        "low confidence. Verify before demoing."
    )

# ---------------------------------------------------------------- tabs

tab_analyse, tab_eval, tab_cat = st.tabs(["Analyse", "Accuracy", "Catalogue"])

# ================================================================ ANALYSE

with tab_analyse:
    st.title("How should this be built?")
    st.caption(
        "Paste a change request. The tool decides the extensibility tier, shows the "
        "evidence behind it, and escalates when there is no clean path."
    )

    picked = st.selectbox(
        "Load a sample requirement",
        ["— write my own —"] + [f"{g['id']}: {g['text'][:70]}…" for g in gold],
    )
    default_text = ""
    if picked != "— write my own —":
        default_text = gold[[f"{g['id']}: {g['text'][:70]}…" for g in gold].index(picked)]["text"]

    text = st.text_area("Change request", value=default_text, height=120)

    if st.button("Analyse", type="primary", disabled=not text.strip()):
        with st.spinner("Reading the requirement, searching the catalogue, applying rules…"):
            st.session_state.trace = pipeline.run(text, catalogue, matrix, rules_cfg)

    trace = st.session_state.get("trace")

    if trace:
        if trace.get("errors"):
            for e in trace["errors"]:
                st.error(e)

        if "structured" in trace:
            s = trace["structured"]

            st.divider()
            st.subheader("1. What was actually asked")
            st.write(s.summary)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Objects", ", ".join(s.business_objects) or "—")
            c2.metric("Action", s.action_type)
            c3.metric("External audience", {True: "yes", False: "no", None: "not stated"}[s.external_consumer])
            c4.metric("Needs new screen", {True: "yes", False: "no", None: "not stated"}[s.needs_custom_ui])

            if s.open_questions:
                st.warning(
                    "**The requirement did not say:**\n\n"
                    + "\n".join(f"- {q}" for q in s.open_questions)
                )

        if "above_floor" in trace:
            st.divider()
            st.subheader("2. What the catalogue returned")
            if not trace["above_floor"]:
                st.error("Nothing scored above the similarity floor.")
            for h in trace["above_floor"]:
                icon = "⛔" if h["type"] == "simplification_item" else "•"
                st.markdown(
                    f"{icon} **{h['id']}** — {h['name']}  \n"
                    f"<span style='color:gray'>tier `{h['tier']}` · score {h['score']} · "
                    f"confidence {h['confidence']} · {h['capability']}</span>",
                    unsafe_allow_html=True,
                )

        if "rule_verdicts" in trace:
            st.divider()
            st.subheader("3. What the rules said")
            for v in trace["rule_verdicts"]:
                if v.severity == "blocker":
                    st.error(f"**{v.rule_id}** → {v.verdict}\n\n{v.reason}")
                else:
                    st.info(f"**{v.rule_id}** → {v.verdict}\n\n{v.reason}")

        if "decision" in trace:
            d = trace["decision"]
            v = trace["validation"]

            st.divider()
            st.subheader("4. Decision")

            tier = v["final_tier"]
            label = TIER_LABELS.get(tier, tier)
            if tier == "escalate":
                st.warning(f"### {label}")
            elif tier in ("configuration", "standard", "key_user"):
                st.success(f"### {label}")
            else:
                st.info(f"### {label}")

            st.write(d.reasoning)

            if v["kept_citations"]:
                st.markdown("**Evidence**")
                by_id = {e["id"]: e for e in catalogue["entries"]}
                for cid in v["kept_citations"]:
                    st.markdown(f"- `{cid}` — {by_id[cid]['name']}")

            if d.rejected_alternatives:
                st.markdown("**Considered and rejected**")
                for r in d.rejected_alternatives:
                    st.markdown(f"- **{TIER_LABELS.get(r.tier, r.tier)}** — {r.reason}")

            st.divider()
            st.subheader("5. Validation")
            if v["citation_valid"] and not v["downgraded"]:
                st.success("Every cited object exists in the catalogue. Nothing was invented.")
            for n in v["notes"]:
                st.error(n)
            if v["disagreement"]:
                st.warning(v["disagreement"])

            st.divider()
            st.subheader("6. Architect gate")
            col_a, col_b = st.columns([1, 2])
            approved = col_a.radio("Decision", ["Approve", "Override"], horizontal=True)
            override_reason = ""
            if approved == "Override":
                override_reason = col_b.text_input("Why? (this is the feedback loop)")

            record = {
                "requirement": text,
                "structured": trace["structured"].model_dump(),
                "rule_verdict": trace["rule_verdict"],
                "model_tier": d.recommended_tier,
                "final_tier": v["final_tier"],
                "reasoning": d.reasoning,
                "citations": v["kept_citations"],
                "stripped_citations": v["stripped_citations"],
                "rejected_alternatives": [r.model_dump() for r in d.rejected_alternatives],
                "confidence": d.confidence,
                "architect_action": approved,
                "override_reason": override_reason,
                "rules_version": rules_cfg["version"],
                "catalogue_version": catalogue["catalogue_version"],
            }
            st.download_button(
                "Download decision record",
                json.dumps(record, indent=2),
                file_name="decision_record.json",
                mime="application/json",
            )
            st.caption(
                f"Plain JSON. No proprietary store, nothing to export from later. "
                f"Took {trace.get('elapsed','—')}s."
            )

# ================================================================ ACCURACY

with tab_eval:
    st.title("Does it actually work?")
    st.caption(
        "Ten labelled requirements. The number that matters is the third one — "
        "how often it escalates when it genuinely should."
    )

    if st.button("Run evaluation", type="primary"):
        results = []
        bar = st.progress(0.0)
        for i, g in enumerate(gold):
            t = pipeline.run(g["text"], catalogue, matrix, rules_cfg)
            if "validation" in t:
                predicted = t["validation"]["final_tier"]
                cited = set(t["validation"]["kept_citations"])
                expected_cites = set(g["expected_citations"])
                results.append({
                    "id": g["id"],
                    "expected": g["expected_tier"],
                    "predicted": predicted,
                    "correct": predicted == g["expected_tier"],
                    "citation_valid": t["validation"]["citation_valid"],
                    "found_expected_citation": bool(expected_cites & cited) or not expected_cites,
                    "difficulty": g["difficulty"],
                })
            bar.progress((i + 1) / len(gold))
        st.session_state.eval = results

    results = st.session_state.get("eval")
    if results:
        n = len(results)
        tier_acc = sum(r["correct"] for r in results) / n
        cite_valid = sum(r["citation_valid"] for r in results) / n

        escalate_cases = [r for r in results if r["expected"] == "escalate"]
        abstain = (
            sum(r["correct"] for r in escalate_cases) / len(escalate_cases)
            if escalate_cases else 0.0
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Tier accuracy", f"{tier_acc:.0%}")
        c2.metric("Citations valid", f"{cite_valid:.0%}")
        c3.metric("Correct escalation", f"{abstain:.0%}", help="Did it escalate when it should have")

        st.dataframe(results, use_container_width=True)
        st.caption(
            "Citations valid means the model never cited an object that does not exist. "
            "This is enforced deterministically, not hoped for."
        )

# ================================================================ CATALOGUE

with tab_cat:
    st.title("The grounded catalogue")
    st.caption(
        "Hand-built for this demo so we could move fast. In an engagement it is "
        "generated from the customer's own system: released APIs from the Business "
        "Accelerator Hub, released CDS views and BAdIs extracted from ADT, "
        "simplification items from the Readiness Check export. Specific to their "
        "release, not generic documentation."
    )
    st.dataframe(
        [
            {k: v for k, v in e.items() if k in
             ("id", "name", "type", "tier", "module", "capability", "confidence")}
            for e in catalogue["entries"]
        ],
        use_container_width=True,
        height=520,
    )
