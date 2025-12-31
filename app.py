import streamlit as st
from engine import get_recommendation_for_ticker
from rag_llm import generate_rag_explanation  # or LLM one

st.title("AI Trade Assistant (Quant + RAG)")

ticker = st.text_input("Enter ticker symbol:", "RELIANCE.NS")

if st.button("Analyze"):
    with st.spinner("Fetching data and computing signals..."):
        rec = get_recommendation_for_ticker(ticker)
        expl = generate_rag_explanation(rec)

    st.subheader("Recommendation")
    st.json(rec)

    st.subheader("Explanation")
    st.markdown(f"```text\n{expl['explanation']}\n```")
