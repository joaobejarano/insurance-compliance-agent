"""
Streamlit Frontend — Insurance Compliance Agent.

Interface para upload de PDF, análise de compliance,
e aprovação humana (human-in-the-loop real).

Rodar: streamlit run app_streamlit.py
"""

import json
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from langgraph.types import Command
import tempfile
import time

# Carrega .env
load_dotenv()

from graph import build_graph


# ═══════════════════════════════════════════════════════
# CONFIG DA PÁGINA
# ═══════════════════════════════════════════════════════

st.set_page_config(
    page_title="Insurance Compliance Agent",
    page_icon="🛡️",
    layout="wide",
)


# ═══════════════════════════════════════════════════════
# INICIALIZAÇÃO (roda uma vez)
# ═══════════════════════════════════════════════════════

@st.cache_resource
def get_agent():
    """Builda o grafo uma vez e reutiliza entre reruns."""
    return build_graph()


def safe_parse(value):
    """Tenta parsear JSON string."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


# ═══════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════

st.title("🛡️ Insurance Compliance Agent")
st.markdown(
    "Upload an insurance policy PDF to analyze compliance gaps, "
    "extract key data, and generate a detailed report."
)
st.divider()


# ═══════════════════════════════════════════════════════
# SIDEBAR — Upload e controles
# ═══════════════════════════════════════════════════════

with st.sidebar:
    st.header("📄 Document Upload")
    
    uploaded_file = st.file_uploader(
        "Upload Insurance Policy PDF",
        type=["pdf"],
        help="Upload a PDF document of an insurance policy to analyze.",
    )
    
    if uploaded_file:
        st.success(f"✅ {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")
    
    st.divider()
    
    analyze_button = st.button(
        "🔍 Analyze Document",
        use_container_width=True,
        type="primary",
        disabled=not uploaded_file,
    )
    
    st.divider()
    st.caption("Built with LangGraph + PyMuPDF + OpenAI")
    st.caption("Sierra Studio — AI Engineer Portfolio")


# ═══════════════════════════════════════════════════════
# PROCESSAMENTO
# ═══════════════════════════════════════════════════════

if analyze_button and uploaded_file:
    # Salva PDF num arquivo temporário
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(uploaded_file.read())
        tmp_path = tmp.name

    agent = get_agent()
    config = {"configurable": {"thread_id": f"st-{uploaded_file.name}-{int(time.time())}"}}

    # ── Roda o agente ──
    with st.status("🔍 Analyzing document...", expanded=True) as status:
        st.write("📋 Classifying document...")
        start_time = time.time()

        try:
            # Roda até o interrupt (human review)
            result = agent.invoke(
                {"messages": [("user", f"Analyze the insurance policy at: {tmp_path}")]},
                config,
            )

            elapsed = time.time() - start_time
            state = agent.get_state(config)

            status.update(label=f"✅ Analysis complete ({elapsed:.1f}s)", state="complete")

        except Exception as e:
            status.update(label="❌ Analysis failed", state="error")
            st.error(f"Error: {str(e)}")
            st.stop()

    # Salva no session_state pra persistir entre reruns
    st.session_state["state"] = state
    st.session_state["config"] = config
    st.session_state["agent"] = agent
    st.session_state["elapsed"] = elapsed
    st.session_state["filename"] = uploaded_file.name

    # Limpa arquivo temporário
    Path(tmp_path).unlink(missing_ok=True)


# ═══════════════════════════════════════════════════════
# RESULTADOS
# ═══════════════════════════════════════════════════════

if "state" in st.session_state:
    state = st.session_state["state"]
    config = st.session_state["config"]
    elapsed = st.session_state["elapsed"]

    values = state.values

    # ── Métricas no topo ──
    col1, col2, col3, col4 = st.columns(4)

    classification = values.get("classification", {})
    compliance = safe_parse(values.get("compliance_result", "{}"))
    if isinstance(compliance, dict):
        comp_status = compliance.get("status", "N/A")
    else:
        comp_status = "N/A"

    col1.metric("Document Type", classification.get("type", "N/A").upper())
    col2.metric("Urgency", classification.get("urgency", "N/A").upper())
    col3.metric("Compliance", comp_status)
    col4.metric("Latency", f"{elapsed:.1f}s")

    st.divider()

    # ── Tabs com resultados detalhados ──
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Classification",
        "📄 Extracted Data",
        "✅ Compliance Check",
        "📊 Report",
    ])

    # ── Tab 1: Classification ──
    with tab1:
        st.subheader("Document Classification")
        if classification:
            cl1, cl2 = st.columns(2)
            with cl1:
                doc_type = classification.get("type", "unknown")
                type_colors = {"policy": "🟢", "claim": "🟡", "complaint": "🔴"}
                st.markdown(f"**Type:** {type_colors.get(doc_type, '⚪')} {doc_type.upper()}")
            with cl2:
                urgency = classification.get("urgency", "unknown")
                urg_color = "🔴" if urgency == "high" else "🟢"
                st.markdown(f"**Urgency:** {urg_color} {urgency.upper()}")

            summary = classification.get("summary", "")
            if summary:
                st.info(f"**Summary:** {summary}")
        else:
            st.warning("No classification data available.")

    # ── Tab 2: Extracted Data ──
    with tab2:
        st.subheader("Extracted Policy Data")
        extracted = safe_parse(values.get("extracted_data"))
        if extracted and isinstance(extracted, dict) and "error" not in extracted:
            # Campos principais em tabela
            main_fields = {
                "Policy Number": extracted.get("policy_number"),
                "Holder Name": extracted.get("holder_name"),
                "Employees": extracted.get("holder_employees"),
                "Business Type": extracted.get("business_type"),
                "Annual Revenue": extracted.get("annual_revenue"),
                "Coverage Type": extracted.get("coverage_type"),
                "Coverage Amount": extracted.get("coverage_amount"),
                "Deductible": extracted.get("deductible"),
                "Annual Premium": extracted.get("premium_annual"),
                "Effective Date": extracted.get("effective_date"),
                "Expiry Date": extracted.get("expiry_date"),
            }

            for field, value in main_fields.items():
                if value is not None:
                    st.markdown(f"**{field}:** {value}")

            st.divider()

            # Listas
            ex1, ex2 = st.columns(2)
            with ex1:
                st.markdown("**Additional Coverages:**")
                for cov in extracted.get("additional_coverages", []):
                    st.markdown(f"- ✅ {cov}")
            with ex2:
                st.markdown("**Exclusions:**")
                for exc in extracted.get("exclusions", []):
                    st.markdown(f"- ❌ {exc}")

            # JSON raw expandível
            with st.expander("🔍 Raw JSON"):
                st.json(extracted)
        else:
            st.warning("No extracted data available.")

    # ── Tab 3: Compliance Check ──
    with tab3:
        st.subheader("Compliance Validation")
        if isinstance(compliance, dict) and "details" in compliance:
            # Status geral
            status_val = compliance.get("status", "N/A")
            if status_val == "PASS":
                st.success(f"✅ COMPLIANCE STATUS: **{status_val}**")
            else:
                st.error(f"❌ COMPLIANCE STATUS: **{status_val}**")

            # Métricas
            cm1, cm2, cm3, cm4 = st.columns(4)
            cm1.metric("Rules Checked", compliance.get("rules_checked", 0))
            cm2.metric("Passed", compliance.get("passed", 0))
            cm3.metric("Failed", compliance.get("failed", 0))
            cm4.metric("Warnings", compliance.get("warnings", 0))

            st.divider()

            # Detalhes por regra
            for detail in compliance.get("details", []):
                rule_status = detail.get("status", "")
                severity = detail.get("severity", "")

                if rule_status == "FAIL":
                    st.error(
                        f"❌ **{detail['rule']}** ({severity})\n\n"
                        f"Requirement: {detail.get('requirement', 'N/A')}\n\n"
                        f"Actual: {detail.get('actual', 'N/A')}"
                    )
                elif rule_status == "WARNING":
                    st.warning(
                        f"⚠️ **{detail['rule']}** ({severity})\n\n"
                        f"Requirement: {detail.get('requirement', 'N/A')}\n\n"
                        f"Actual: {detail.get('actual', 'N/A')}"
                    )
                else:
                    st.success(
                        f"✅ **{detail['rule']}**\n\n"
                        f"Requirement: {detail.get('requirement', 'N/A')}\n\n"
                        f"Actual: {detail.get('actual', 'N/A')}"
                    )
        else:
            st.warning("No compliance data available.")

    # ── Tab 4: Report ──
    with tab4:
        st.subheader("Compliance Report")
        report = values.get("report")
        if report:
            st.code(report, language=None)
        else:
            st.warning("No report available.")

    # ═══════════════════════════════════════════════════════
    # HUMAN-IN-THE-LOOP: Aprovação real
    # ═══════════════════════════════════════════════════════

    st.divider()
    st.subheader("🙋 Human Review")
    st.markdown(
        "Review the analysis above and approve or reject. "
        "This simulates the human-in-the-loop step in production."
    )

    # Verifica se já foi aprovado
    if values.get("approved") is not None:
        if values.get("approved"):
            st.success("✅ This analysis has been **APPROVED**.")
        else:
            st.error("❌ This analysis has been **REJECTED**.")
    else:
        # Botões de aprovação
        col_approve, col_reject = st.columns(2)

        with col_approve:
            if st.button("✅ Approve", use_container_width=True, type="primary"):
                agent = st.session_state["agent"]
                try:
                    agent.invoke(
                        Command(resume={"approved": True}),
                        config,
                    )
                    st.session_state["state"] = agent.get_state(config)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

        with col_reject:
            feedback = st.text_input("Rejection feedback (optional):")
            if st.button("❌ Reject", use_container_width=True):
                agent = st.session_state["agent"]
                try:
                    agent.invoke(
                        Command(resume={
                            "approved": False,
                            "feedback": feedback or "Analysis rejected by human reviewer.",
                        }),
                        config,
                    )
                    st.session_state["state"] = agent.get_state(config)
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
