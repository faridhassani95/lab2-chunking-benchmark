# LLM Engineer Lab 2 — Chunking Benchmark

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FAISS](https://img.shields.io/badge/FAISS-1.15-green)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-teal)
![Sentence Transformers](https://img.shields.io/badge/Sentence--Transformers-all--MiniLM--L6--v2-orange)
![Ollama](https://img.shields.io/badge/Ollama-Llama%203.2-purple)
![Docker](https://img.shields.io/badge/Docker-ready-blue)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

> **Scientific Question:** Which chunking strategy produces the highest retrieval quality for a RAG system on Java documentation?

---

## 📊 Key Results

Evaluated on **50 queries** across **5 categories** (direct, conceptual, multi-concept, indirect, multi-source).

| Strategy | Chunks | MRR | Recall@5 | Precision@5 | Efficiency* |
|----------|--------|-----|----------|-------------|-------------|
| **Character** | 961 | **0.900** | **0.980** | **0.780** | 0.937 |
| Recursive | 989 | 0.885 | **0.980** | 0.748 | 0.895 |
| Semantic | 2,990 | **0.902** | 0.930 | 0.760 | 0.302 |
| LLM | **826** | 0.897 | **0.980** | 0.720 | **1.086** |

*\*Efficiency = MRR / Number of Chunks × 1000 (higher = better quality per chunk)*

### 🏆 Engineering Verdict

> **Character Chunking — the simplest baseline — matched complex methods at a fraction of the cost.**

---

## 📈 Charts

<p align="center">
  <img src="reports/metrics_comparison.png" width="400" />
  <img src="reports/chunk_distribution.png" width="400" />
  <img src="reports/mrr_comparison.png" width="400" />
</p>

---

## 🔬 Performance by Query Type

| Query Type | Best MRR | Best Strategy |
|------------|----------|---------------|
| Direct | 1.000 | All strategies |
| Conceptual | 0.950 | LLM |
| Multi-concept | 0.950 | Character |
| **Indirect** | **0.800** | **Semantic** |
| Multi-source | 0.950 | Character |

---

## 🛠️ Chunking Strategies

| # | Strategy | How It Works |
|---|----------|--------------|
| 1 | **Character** | Fixed 1000-char windows with 200-char overlap |
| 2 | **Recursive** | Splits by paragraph → sentence → line → word |
| 3 | **Semantic** | Groups sentences by embedding similarity (MiniLM, threshold=0.5) |
| 4 | **LLM** | Local Llama predicts breakpoint indices (lossless, boundary method) |

---

## 📐 Metrics

| Metric | Definition |
|--------|------------|
| **Recall@k** | Fraction of relevant classes found in top-k |
| **Precision@k** | Fraction of top-k that are actually relevant |
| **MRR** | Mean Reciprocal Rank (1 / rank of first relevant) |
| **Efficiency** | MRR per 1000 chunks (custom quality-to-cost ratio) |

---

## 🚀 Quick Start

```bash
pip install -r requirements.txt
python src/evaluation/benchmark.py
python api/main.py
# Open http://localhost:8000
👤 Author
Farid Hassani — LLM Engineer in Training

"I don't choose my chunking strategy based on hype. I benchmark it."

📂 Project Structure
text
lab-2-chunking-benchmark/
├── api/              # FastAPI RAG server
├── data/
│   ├── chunks/       # JSON chunks + benchmark results
│   ├── processed/    # Cleaned markdown
│   └── raw/          # Original HTML
├── src/
│   ├── chunkers/     # 4 strategies
│   ├── data/         # Cleaner
│   └── evaluation/   # Benchmark + 50 queries
├── reports/          # Charts (PNG)
├── Dockerfile
└── README.md
