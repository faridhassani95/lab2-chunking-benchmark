```markdown
# LLM Engineer Lab 2 — Chunking Benchmark

> Scientific Question: Which chunking strategy produces the highest retrieval quality for a RAG system on Java documentation?

## Overview

This lab benchmarks 4 generations of chunking strategies on real Java SE documentation to answer an engineering question with evidence, not opinion.

| Strategy | Generation | Approach |
|----------|-----------|----------|
| Character | 1st Gen | Fixed-size character splits |
| Recursive | 2nd Gen | Separator-aware (paragraph to sentence to word) |
| Semantic | 3rd Gen | Embedding similarity between sentences |
| LLM-based | 4th Gen | Local LLM (Llama) predicts concept boundaries |

---

## Key Results

Evaluated on 50 queries across 5 categories (direct, conceptual, multi-concept, indirect, multi-source).

| Strategy | Chunks | MRR | Recall@5 | Precision@5 | Efficiency* |
|----------|--------|-----|----------|-------------|-------------|
| Character | 961 | 0.900 | 0.980 | 0.780 | 0.937 |
| Recursive | 989 | 0.885 | 0.980 | 0.748 | 0.895 |
| Semantic | 2990 | 0.902 | 0.930 | 0.760 | 0.302 |
| LLM | 826 | 0.897 | 0.980 | 0.720 | 1.086 |

*Efficiency = MRR / Number of Chunks x 1000 (custom decision-support metric, higher is better)

### Engineering Verdict

Character Chunking, the simplest baseline, achieved comparable retrieval quality to LLM and Semantic methods while being significantly cheaper and faster. On this dataset, complex chunking strategies did not provide a meaningful retrieval-quality improvement over the fixed-size baseline.

---

## Performance by Query Type

Hard queries revealed where strategies differ:

| Query Type | Best MRR | Best Strategy |
|------------|----------|---------------|
| Direct | 1.000 | All strategies |
| Conceptual | 0.950 | LLM |
| Multi-concept | 0.950 | Character |
| Indirect | 0.800 | Semantic |
| Multi-source | 0.950 | Character |

Takeaway: Semantic chunking shines on indirect questions (where the class name is not mentioned), while Character is surprisingly robust everywhere else.

---

## Evaluation Pipeline

Java Docs (17 files, 18,917 lines) -> Clean & Normalize -> 4 Chunkers (Character, Recursive, Semantic, LLM) -> all-MiniLM-L6-v2 Embedding -> FAISS Vector Search -> 50 Multi-type Queries -> Recall@k, Precision@k, MRR -> Efficiency Analysis, Decision Matrix

---

## Chunking Strategies

### 1. Character Chunker
- Fixed 1000-char windows with 200-char overlap
- Zero language understanding, pure baseline
- Strengths: Fastest, deterministic, zero cost
- Weaknesses: Can split mid-word or mid-concept

### 2. Recursive Chunker
- Separator hierarchy: paragraph, sentence, line, word
- Respects paragraph and sentence boundaries
- Strengths: Deterministic, preserves structure
- Weaknesses: No semantic awareness

### 3. Semantic Chunker
- Splits sentences, embeds with all-MiniLM-L6-v2
- Groups sentences by cosine similarity (threshold = 0.5)
- Strengths: Understands topic changes, best on indirect queries
- Weaknesses: 3x more chunks, higher embedding cost

### 4. LLM-based Chunker (Boundary Index Method)
- Sends numbered sentences to local Llama model via Ollama
- LLM returns breakpoint indices only, fully lossless
- Post-processed with min/max constraints (300-1200 chars)
- Strengths: Fewest chunks, good conceptual grouping
- Weaknesses: Slowest to generate, non-deterministic, requires GPU

---

## Metrics

| Metric | Definition |
|--------|------------|
| Recall@k | Fraction of relevant classes found in top-k results |
| Precision@k | Fraction of top-k results that are actually relevant |
| MRR | Mean Reciprocal Rank, 1 divided by rank of first relevant item |
| Efficiency Score | MRR per 1000 chunks, quality-to-cost ratio (custom metric) |

---

## Production RAG API

A FastAPI server exposes all 4 chunking strategies via a single endpoint.

GET /search?q=How+to+create+a+String&strategy=character&k=3

Start with: python api/main.py then open http://localhost:8000

Features: Configurable chunking strategy, streaming responses, Docker-ready (Dockerfile included)

---

## Project Structure

lab-2-chunking-benchmark/
- data/processed/java_docs/final/ (17 cleaned MD files)
- data/chunks/ (chunked output and benchmark results in JSON)
- data/raw/java_docs/html/ (original HTML files)
- src/data/cleaner.py (document cleaning pipeline)
- src/chunkers/ (4 chunking strategies)
- src/evaluation/ (benchmark suite and 50 queries)
- api/main.py (production RAG API)
- reports/ (generated charts in PNG)
- Dockerfile
- requirements.txt
- README.md

---

## Quick Start

pip install -r requirements.txt

python src/chunkers/character_chunker.py
python src/chunkers/recursive_chunker.py
python src/chunkers/semantic_chunker.py
python src/chunkers/llm_chunker.py

python src/evaluation/benchmark.py

python api/main.py

---

## Limitations and Future Work

- Query set size: 50 queries is sufficient for a portfolio lab but not production-level.
- Embedding model: all-MiniLM-L6-v2 is lightweight. Testing with stronger models may reveal larger differences.
- Ground truth granularity: Relevance measured at document level, not chunk level.
- LLM Chunker cost: Latency and GPU cost not benchmarked here.
- Docker: Dockerfile included but not tested due to Iran internet limitations on Kali VM.

---

## Author

Farid Hassani — LLM Engineer in training.

"I don't choose my chunking strategy based on hype. I benchmark it."

Lab 2 of 7 — LLM Engineer Portfolio Roadmap
```