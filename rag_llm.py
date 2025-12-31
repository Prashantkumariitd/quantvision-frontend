# rag_llm.py

import os
from typing import List, Dict
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np

# ---------- 1. LOAD / INITIALIZE KNOWLEDGE BASE ----------

KB_DIR = "kb"
os.makedirs(KB_DIR, exist_ok=True)

# If kb/ is empty, create some default files
if not os.listdir(KB_DIR):
    files_content = {
        "market_regimes.md": """
Bull-Low-Vol Regime:
This regime indicates a stable uptrend with controlled volatility. Trend-following strategies and momentum-based entries tend to perform well. Risk is lower compared to high-volatility regimes.

Bull-High-Vol Regime:
This regime represents a strong uptrend with high volatility. Gains can be fast but drawdowns are also sharp. Breakout trades work well but position sizing and stop-loss placement are critical.

Bear Regime:
This regime indicates a dominant downtrend. Long positions are risky. Short-selling and defensive strategies dominate.

Sideways Regime:
No clear directional trend. Mean-reversion strategies perform better than trend or breakout strategies.
""",
        "rsi_explained.md": """
RSI (Relative Strength Index) measures momentum on a scale of 0 to 100.

RSI above 55 indicates bullish momentum.
RSI below 45 indicates bearish momentum.
RSI between 45 and 55 is considered neutral.

RSI performs best when combined with trend context. High RSI in a bull market suggests continuation, while high RSI in a sideways market can indicate exhaustion.
""",
        "trend_following.md": """
Trend following assumes that price movement persists in the same direction.

Moving average crossovers are a basic trend-following signal.
When short-term MA moves above long-term MA, momentum is considered bullish.
Trend strategies work best in strong, directional markets and fail in choppy sideways markets.
""",
        "breakout_strategies.md": """
Breakout strategies attempt to capture large directional moves after price exits a range.

Breakouts above recent highs indicate bullish strength.
Breakdowns below recent lows indicate bearish weakness.
False breakouts are common in low-volume or low-volatility environments.
""",
        "risk_management.md": """
Risk management controls losses and protects capital.

Never risk more than a small percentage of capital on a single trade.
Use stop-loss orders to prevent catastrophic losses.
High-volatility regimes require smaller position sizes.
No strategy works all the time; drawdowns are unavoidable.
"""
    }
    for fname, content in files_content.items():
        path = os.path.join(KB_DIR, fname)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content.strip() + "\n")

# Load KB into memory
_docs: List[str] = []
_sources: List[str] = []

for fname in os.listdir(KB_DIR):
    path = os.path.join(KB_DIR, fname)
    if not os.path.isfile(path):
        continue
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    _docs.append(text.strip())
    _sources.append(fname)

_clean_docs = [d for d in _docs if d.strip()]
_clean_sources = [s for s, d in zip(_sources, _docs) if d.strip()]

_vectorizer = TfidfVectorizer()
_doc_matrix = _vectorizer.fit_transform(_clean_docs)


# ---------- 2. RAG RETRIEVAL ----------

def retrieve_kb_docs(query: str, k: int = 3) -> List[Dict]:
    """
    Return top-k KB docs most relevant to the query using TF-IDF.
    """
    q_vec = _vectorizer.transform([query])
    scores = (_doc_matrix @ q_vec.T).toarray().ravel()
    topk_idx = scores.argsort()[::-1][:k]

    results = []
    for i in topk_idx:
        results.append({
            "source": _clean_sources[i],
            "score": float(scores[i]),
            "text": _clean_docs[i],
        })
    return results


# ---------- 3. SIMPLE RAG-BASED EXPLANATION (no LLM) ----------

def generate_rag_explanation(rec: dict, k: int = 3) -> Dict:
    """
    Use KB + signals to build a human-readable explanation WITHOUT an LLM.
    Returns a dict with 'explanation' and 'kb_sources'.
    """

    query = f"""
    Explain this trade setup.

    Ticker: {rec.get('ticker', 'N/A')}
    Action: {rec['action']}
    Market Regime: {rec['market_regime']}
    RSI: {rec['rsi']}
    Trend Signal: {rec['trend_signal']}
    RSI Signal: {rec['rsi_signal']}
    Breakout Signal: {rec['breakout_signal']}
    ML Probability: {rec.get('ml_prob_profitable')}
    """

    kb_hits = retrieve_kb_docs(query, k=k)

    lines = []
    lines.append(f"Recommended action: {rec['action']} on {rec.get('ticker', 'this asset')}.")
    lines.append(f"Current market regime: {rec['market_regime']}, RSI = {rec['rsi']}.")
    lines.append("Signals:")
    lines.append(f"  • Trend signal    = {rec['trend_signal']} (1 = bullish, 0 = neutral).")
    lines.append(f"  • RSI signal      = {rec['rsi_signal']} (1 = bullish, -1 = bearish).")
    lines.append(f"  • Breakout signal = {rec['breakout_signal']} (1 = breakout, -1 = breakdown).")

    ml_prob = rec.get("ml_prob_profitable")
    if ml_prob is not None:
        lines.append(f"Model-estimated probability of a profitable outcome ≈ {ml_prob:.2f}.")

    lines.append("")
    lines.append("Context from knowledge base:")

    for hit in kb_hits:
        lines.append(f"\nFrom {hit['source']} (score {hit['score']:.3f}):")
        snippet = hit["text"].replace("\n", " ").strip()
        if len(snippet) > 350:
            snippet = snippet[:350] + "..."
        lines.append(f"  {snippet}")

    lines.append("")
    lines.append("Reminder: Markets are noisy and no strategy works all the time. Use position sizing and stop-losses to control risk.")

    explanation_text = "\n".join(lines)

    return {
        "explanation": explanation_text,
        "kb_sources": [h["source"] for h in kb_hits],
    }


# ---------- 4. OPTIONAL: LLM-BASED EXPLANATION ----------

try:
    from openai import OpenAI
    import textwrap
    _client = OpenAI()
except Exception:
    _client = None


def generate_llm_explanation(rec: dict, k: int = 3, model_name: str = "gpt-5.1-mini") -> str:
    """
    Use RAG + OpenAI LLM to generate a nicer explanation.
    Requires OPENAI_API_KEY in the environment and openai installed.
    """
    if _client is None:
        raise RuntimeError("OpenAI client not available. Install 'openai' and set OPENAI_API_KEY.")

    kb_hits = retrieve_kb_docs(
        f"Action {rec['action']}, regime {rec['market_regime']}, RSI {rec['rsi']}, signals {rec['trend_signal']}, {rec['rsi_signal']}, {rec['breakout_signal']}",
        k=k
    )

    context_chunks = []
    for hit in kb_hits:
        snippet = hit["text"].strip()
        if len(snippet) > 600:
            snippet = snippet[:600] + "..."
        context_chunks.append(f"From {hit['source']}:\n{snippet}")
    context_text = "\n\n".join(context_chunks)

    state_summary = f"""
    Ticker: {rec.get('ticker', 'N/A')}
    Price: {rec['price']}
    Market Regime: {rec['market_regime']}
    RSI: {rec['rsi']}
    Trend Signal: {rec['trend_signal']}
    RSI Signal: {rec['rsi_signal']}
    Breakout Signal: {rec['breakout_signal']}
    ML Probability of Profitable Outcome: {rec.get('ml_prob_profitable')}
    Action: {rec['action']}
    """

    prompt = f"""
    You are an explainable trading assistant. 
    You MUST be cautious: never promise profit and always mention risk.

    CONTEXT FROM KNOWLEDGE BASE:
    {context_text}

    CURRENT SIGNAL STATE:
    {state_summary}

    TASK:
    1. In 2–4 short paragraphs, explain why this action (BUY / SELL / NO TRADE) could make sense
       given the market regime and signals.
    2. Explicitly describe the main RISKS and when this trade can go wrong.
    3. Keep the language clear and understandable for a non-quant.
    4. Do NOT invent numbers; use only the information provided.
    """

    completion = _client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": "You are a careful, realistic trading explainer. Never guarantee profits."},
            {"role": "user", "content": textwrap.dedent(prompt).strip()},
        ],
        temperature=0.4,
    )

    return completion.choices[0].message.content
