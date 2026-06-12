"""
Project 1 — AI Document Summarizer
Streamlit UI — clean, simple, 4 pages
"""

import streamlit as st
import os
import json
from dotenv import load_dotenv
from bedrock_client import upload_to_s3, call_summarize_api
import requests

load_dotenv()

# ── Page config ──
st.set_page_config(
    page_title="AI Document Summarizer",
    page_icon="📄",
    layout="wide"
)

# ── Document type mapping ──
DOC_TYPES = {
    "General Document": "general",
    "SEC Filing (10-K / 10-Q)": "sec_10k",
    "Insurance Claim": "insurance_claim",
    "Loan Document": "loan_document",
    "Legal Contract": "legal_contract",
    "Research Report": "research_report"
}

# ── Sidebar navigation ──
st.sidebar.title("📄 Doc Summarizer")
st.sidebar.markdown("---")
page = st.sidebar.radio(
    "Navigate",
    ["Try it out", "How it works", "Architecture", "About"]
)
st.sidebar.markdown("---")
st.sidebar.caption("Built on AWS · Powered by Amazon Bedrock")

# ============================================================
# PAGE 1: TRY IT OUT
# ============================================================
if page == "Try it out":
    st.title("AI Document Summarizer")
    st.markdown("Upload a PDF or TXT file and get an AI-generated summary powered by Amazon Bedrock.")
    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("1. Select document type")
        doc_type_label = st.selectbox(
            "Document type",
            list(DOC_TYPES.keys()),
            label_visibility="collapsed"
        )
        doc_type = DOC_TYPES[doc_type_label]

        st.subheader("2. Upload your document")
        uploaded_file = st.file_uploader(
            "Upload PDF or TXT file",
            type=["pdf", "txt"],
            help="Supported formats: PDF, TXT. Maximum size: 10MB."
        )

        st.markdown("---")
        summarize_btn = st.button(
            "Generate Summary",
            type="primary",
            use_container_width=True
        )

    with col2:
        st.subheader("Summary")

        if summarize_btn:
            if not uploaded_file:
                st.error("📁 Please upload a document first.")
            elif uploaded_file.size == 0:
                st.error("📄 The uploaded file is empty. Please choose a different file.")
            elif uploaded_file.size > 10 * 1024 * 1024:
                st.error(f"📦 File too large ({uploaded_file.size / (1024*1024):.1f}MB). Maximum size is 10MB.")
            else:
                with st.spinner("Analyzing document... this may take 5-15 seconds"):
                    try:
                        # Read file
                        file_bytes = uploaded_file.read()
                        filename = uploaded_file.name

                        # Upload to S3
                        s3_key = upload_to_s3(file_bytes, filename)

                        # Call API Gateway
                        result = call_summarize_api(s3_key, doc_type)

                        # result is already unwrapped by bedrock_client
                        if 'summary' in result:
                            st.success("✅ Summary generated successfully!")
                            escaped_summary = result['summary'].replace('$', '\\$')
                            st.markdown(escaped_summary)
                            st.markdown("---")
                            st.caption(f"Model: {result.get('model_id', 'Claude Haiku 4.5')}")
                        elif 'error' in result:
                            error_msg = result['error']
                            if 'extract text' in error_msg.lower():
                                st.error("📄 Could not extract text from this document. It may be a scanned image or corrupted file.")
                            elif 's3_key is required' in error_msg.lower():
                                st.error("📁 Upload failed. Please try again.")
                            else:
                                st.error(f"⚠️ Error: {error_msg}")
                        elif 'message' in result and 'timed out' in str(result.get('message', '')).lower():
                            st.error("⏱️ The request took too long to process. Try a smaller document (under 15 pages recommended).")
                        else:
                            st.error(f"⚠️ Unexpected response format: {str(result)[:200]}")

                    except requests.exceptions.Timeout:
                        st.error("⏱️ Request timed out. The document may be too large or complex. Try a smaller file.")
                    except requests.exceptions.ConnectionError:
                        st.error("🔌 Could not connect to the API. Please check your internet connection and try again.")
                    except Exception as e:
                        st.error(f"⚠️ Something went wrong: {str(e)}")
        else:
            st.info("👈 Select a document type and upload a file to get started.")

# ============================================================
# PAGE 2: HOW IT WORKS
# ============================================================
elif page == "How it works":
    st.title("How it works")
    st.markdown("---")

    st.markdown("""
    This app uses a fully serverless pipeline on AWS to summarize
    documents using AI. Here is what happens when you click **Generate Summary**:
    """)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("### Step 1 — Upload")
        st.markdown("""
        Your document is uploaded directly to **Amazon S3** — a secure,
        private cloud storage bucket. The file is stored securely in S3 before processing.
        """)

        st.markdown("### Step 2 — Process")
        st.markdown("""
        **AWS Lambda** receives the request via **API Gateway**.
        It reads your document from S3 and extracts the text content.
        For PDFs, the first 15 pages are processed — this covers the
        most important sections of most reports while keeping
        response times fast and within API Gateway's 29-second limit.
        """)

        st.markdown("### Step 3 — Summarize")
        st.markdown("""
        Lambda sends the document text to **Amazon Bedrock** running
        **Claude Haiku 4.5**. The prompt is tailored to your document
        type for more relevant results.
        """)

    with col2:
        st.markdown("### Step 4 — Return")
        st.markdown("""
        The summary travels back through API Gateway to Streamlit
        and is displayed here. The round trip typically takes 5-15 seconds depending on document size.
        """)

        st.markdown("### Why serverless?")
        st.markdown("""
        Every component is serverless — no servers running when idle.
        You only pay for what you use. Cost per summary: less than $0.01.
        """)

        st.markdown("### Model flexibility")
        st.markdown("""
        The AI model ID is stored in **AWS SSM Parameter Store**.
        Upgrading to a better model requires changing one parameter —
        no code changes, no redeployment.
        """)

    st.markdown("---")
    st.markdown("### Tech stack")
    cols = st.columns(4)
    with cols[0]:
        st.metric("Frontend", "Streamlit")
        st.metric("Runtime", "AWS Lambda")
    with cols[1]:
        st.metric("API", "API Gateway")
        st.metric("Storage", "Amazon S3")
    with cols[2]:
        st.metric("AI", "Claude Haiku 4.5")
        st.metric("Config", "SSM Param Store")
    with cols[3]:
        st.metric("IaC", "Terraform + CF")
        st.metric("Language", "Python 3.12")

# ============================================================
# PAGE 3: ARCHITECTURE
# ============================================================
elif page == "Architecture":
    st.title("Architecture")
    st.markdown("---")

    st.markdown("""
    ### Serverless Document Intelligence Pipeline

    Fully serverless architecture on AWS. All infrastructure
    provisioned as code using **Terraform** and **CloudFormation**.
    """)

    st.info("📐 Architecture diagram will be added here on Day 12.")

    st.markdown("---")
    st.markdown("### Component breakdown")

    components = {
        "Streamlit": "Python web UI. Handles file upload and displays results.",
        "API Gateway": "Managed REST endpoint. Handles HTTPS and routes POST /summarize to Lambda.",
        "AWS Lambda": "Serverless orchestrator. Reads S3, calls Bedrock, returns summary.",
        "Amazon S3": "Private object storage. Stores uploaded documents. AES256 encrypted, no public access.",
        "Amazon Bedrock": "Managed AI service running Claude Haiku 4.5. Pay-per-token pricing.",
        "SSM Parameter Store": "Stores the Bedrock model ID. Change model without touching code.",
        "IAM Role": "Least-privilege execution role. Lambda only gets S3 read, Bedrock invoke, SSM read.",
        "Terraform + CloudFormation": "All infrastructure as code. Reproducible on any AWS account."
    }

    for component, description in components.items():
        with st.expander(f"**{component}**"):
            st.markdown(description)

# ============================================================
# PAGE 4: ABOUT
# ============================================================
elif page == "About":
    st.title("About this project")
    st.markdown("---")

    st.markdown("### Gen AI on AWS — Portfolio Project")
    st.markdown("🔗 [View on GitHub](https://github.com/prk-gen-ai-aws/genai-aws-p01-document-summarizer)")
    st.markdown("---")
    st.markdown("""
    Part of an ongoing series exploring Gen AI on AWS — applying
    real-world architecture patterns from serverless foundations
    to multi-agent agentic systems.

    Built with real-world practices:
    - **IaC** — Terraform + CloudFormation
    - **Least-privilege IAM** — Lambda only has what it needs
    - **Serverless-first** — cost-effective on a personal AWS account
    - **Fork-friendly** — clone, fill one file, run one command
    """)

    st.markdown("---")
    st.markdown("### What this project demonstrates")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        **Cloud Architecture:**
        - Serverless pipeline design
        - API Gateway + Lambda integration
        - S3 for decoupled file handling
        - SSM for centralized configuration
        """)
    with col2:
        st.markdown("""
        **Gen AI Engineering:**
        - Amazon Bedrock API integration
        - Document-type-aware prompting
        - Document-type-aware AI prompting
        - Model-agnostic design via SSM
        """)

    st.markdown("---")
    st.markdown("### Things to consider at scale")
    st.markdown("""
    | Concern | Consideration |
    |---|---|
    | **Security** | VPC endpoints, Bedrock Guardrails, encryption at rest |
    | **Scalability** | Lambda concurrency limits, Bedrock quota increases |
    | **High Availability** | Multi-region, Lambda retry with backoff, DLQ |
    | **Cost** | Prompt caching, token budgeting, CloudWatch dashboards |
    """)


