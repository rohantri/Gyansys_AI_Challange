import streamlit as st
import sys, os, traceback

st.title("Diagnostics")
st.write("Python:", sys.version)
st.write("Working dir:", os.getcwd())

st.subheader("Files present")
for root, dirs, files in os.walk("."):
    dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv")]
    for f in files:
        st.text(os.path.join(root, f))

st.subheader("Imports")
for mod in ["numpy", "pandas", "yaml", "pydantic", "google.generativeai"]:
    try:
        __import__(mod)
        st.success(f"{mod} ok")
    except Exception:
        st.error(f"{mod} FAILED")
        st.code(traceback.format_exc())

st.subheader("Engine package")
try:
    from engine import llm, retrieval, rules, pipeline
    st.success("engine imports ok")
except Exception:
    st.error("engine FAILED")
    st.code(traceback.format_exc())

st.subheader("Secrets")
try:
    st.write("GEMINI_API_KEY present:", "GEMINI_API_KEY" in st.secrets)
except Exception as e:
    st.error(f"secrets unreadable: {e}")
