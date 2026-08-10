"""
Lab 2 — Chunking Benchmark: Professional Retrieval Evaluation Suite

Evaluates 4 chunking strategies (Character, Recursive, Semantic, LLM)
using 50 multi-type queries with multi-source ground truth.

Metrics:
    - Recall@k (multi-source aware)
    - Precision@k
    - MRR (Mean Reciprocal Rank)
    - Per-category breakdown
    - Efficiency Score (MRR per 100 chunks)
    - Decision Matrix (Quality vs Cost trade-off)
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from sentence_transformers import SentenceTransformer
import faiss
import time


class ChunkingBenchmark:
    """Professional retrieval evaluation for chunking strategies."""

    def __init__(
        self,
        embedding_model: str = "all-MiniLM-L6-v2",
        chunks_dir: str = "data/chunks",
        queries_path: str = "src/evaluation/queries.json",
        results_path: str = "data/chunks/benchmark_results.json",
    ):
        self.embedding_model = embedding_model
        self.chunks_dir = Path(chunks_dir)
        self.queries_path = Path(queries_path)
        self.results_path = Path(results_path)

        print(f"Loading embedding model: {embedding_model}...")
        self.model = SentenceTransformer(embedding_model)
        self._indices = {}
        self._chunks = {}

    def load_chunks(self, strategy: str) -> List[Dict]:
        """Load chunked documents for a given strategy."""
        file_path = self.chunks_dir / f"chunks_{strategy}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Chunk file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def build_index(self, strategy: str) -> faiss.IndexFlatIP:
        """Build or retrieve cached FAISS index for a strategy."""
        if strategy in self._indices:
            return self._indices[strategy]

        chunks = self.load_chunks(strategy)
        self._chunks[strategy] = chunks
        texts = [c["text"] for c in chunks]
        print(f"  Building index for {strategy} ({len(texts)} chunks)...")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=True,
            normalize_embeddings=True,
            batch_size=32,
        )
        dim = embeddings.shape[1]
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings.astype(np.float32))
        self._indices[strategy] = index
        return index

    def evaluate(
        self,
        strategy: str,
        queries: List[Dict],
        k_values: List[int] = [1, 3, 5],
    ) -> Dict:
        """
        Evaluate a chunking strategy on test queries.
        Supports multi-source relevance.
        """
        print(f"\n{'='*60}")
        print(f"Evaluating: {strategy}")
        print(f"{'='*60}")

        chunks = self._chunks.get(strategy)
        if not chunks:
            chunks = self.load_chunks(strategy)
            self._chunks[strategy] = chunks
        index = self.build_index(strategy)

        recall = {k: [] for k in k_values}
        precision = {k: [] for k in k_values}
        mrr_scores = []
        category_metrics = {}

        start_time = time.time()

        for query_item in queries:
            query_text = query_item["query"]
            relevant_classes = [rc.lower() for rc in query_item["relevant_classes"]]
            query_type = query_item.get("type", "unknown")

            # Encode and search
            query_emb = self.model.encode([query_text], normalize_embeddings=True)
            scores, indices = index.search(query_emb.astype(np.float32), max(k_values))

            retrieved_classes = [
                chunks[idx]["metadata"]["source"].lower() for idx in indices[0]
            ]

            # Compute per-k metrics
            for k in k_values:
                top_k = retrieved_classes[:k]

                # Recall: fraction of relevant classes found
                found = sum(1 for rc in relevant_classes if rc in top_k)
                recall[k].append(found / len(relevant_classes))

                # Precision: fraction of retrieved that are relevant
                hits = sum(1 for c in top_k if c in relevant_classes)
                precision[k].append(hits / k)

            # MRR: rank of first relevant item (any relevant class)
            try:
                first_rank = min(
                    retrieved_classes.index(rc) + 1
                    for rc in relevant_classes
                    if rc in retrieved_classes
                )
                mrr = 1.0 / first_rank
            except ValueError:
                mrr = 0.0
            mrr_scores.append(mrr)

            # Per-category tracking (using Recall@5 and MRR)
            if query_type not in category_metrics:
                category_metrics[query_type] = {"recall5": [], "mrr": []}
            cat_recall5 = (
                sum(1 for rc in relevant_classes if rc in retrieved_classes[:5])
                / len(relevant_classes)
            )
            category_metrics[query_type]["recall5"].append(cat_recall5)
            category_metrics[query_type]["mrr"].append(mrr)

        elapsed = time.time() - start_time

        # Aggregate results
        results = {
            "strategy": strategy,
            "num_queries": len(queries),
            "num_chunks": len(chunks),
            "eval_time_sec": round(elapsed, 1),
        }

        for k in k_values:
            results[f"recall@{k}"] = float(np.mean(recall[k]))
            results[f"precision@{k}"] = float(np.mean(precision[k]))
        results["mrr"] = float(np.mean(mrr_scores))

        # Per-category
        results["by_category"] = {}
        for cat, metrics in category_metrics.items():
            results["by_category"][cat] = {
                "recall@5": float(np.mean(metrics["recall5"])),
                "mrr": float(np.mean(metrics["mrr"])),
                "num_queries": len(metrics["recall5"]),
            }

        return results

    def run_full_benchmark(
        self,
        strategies: List[str] = ["character", "recursive", "semantic", "llm"],
    ) -> List[Dict]:
        """Run evaluation on all strategies."""
        if not self.queries_path.exists():
            raise FileNotFoundError(
                f"Queries file not found: {self.queries_path}"
            )
        with open(self.queries_path, "r", encoding="utf-8") as f:
            queries = json.load(f)
        print(f"Loaded {len(queries)} queries from {self.queries_path}")

        results = []
        for strategy in strategies:
            result = self.evaluate(strategy, queries)
            results.append(result)
            self._print_result(result)

        # Save raw results
        self.results_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.results_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)
        print(f"\nRaw results saved to: {self.results_path}")

        return results

    def _print_result(self, result: Dict):
        """Print evaluation result in a professional format."""
        print(f"\n  Strategy: {result['strategy']}")
        print(f"  Queries: {result['num_queries']} | Chunks: {result['num_chunks']} | Time: {result['eval_time_sec']}s")
        for metric in ["recall@1", "recall@3", "recall@5", "precision@1", "precision@3", "precision@5", "mrr"]:
            if metric in result:
                print(f"  {metric.upper():12s}: {result[metric]:.3f}")

        if "by_category" in result:
            print("\n  Performance by Query Type:")
            for cat in sorted(result["by_category"].keys()):
                m = result["by_category"][cat]
                print(f"    {cat:20s}: Recall@5={m['recall@5']:.3f}, MRR={m['mrr']:.3f} ({m['num_queries']} queries)")

    # ------------------------------------------------------------------
    # Advanced Analysis: Efficiency, Trade-offs, Decision Matrix
    # ------------------------------------------------------------------
    @staticmethod
    def generate_analysis_report(results: List[Dict]) -> Dict:
        """
        Compute efficiency scores and produce a decision matrix.
        """
        print("\n" + "=" * 60)
        print("ADVANCED ANALYSIS: Quality-Efficiency Trade-off")
        print("=" * 60)

        # Build table
        analysis = []
        for r in results:
            chunks = r["num_chunks"]
            mrr = r["mrr"]
            # Efficiency: MRR per 100 chunks (higher is better)
            efficiency = (mrr / chunks) * 1000  # scaled
            # Cost estimation (relative): LLM > Semantic > Recursive > Character
            cost_map = {"character": 1, "recursive": 2, "semantic": 4, "llm": 6}
            estimated_cost = cost_map.get(r["strategy"], 3)

            analysis.append({
                "strategy": r["strategy"],
                "mrr": mrr,
                "chunks": chunks,
                "efficiency_score": round(efficiency, 3),
                "estimated_cost": estimated_cost,
            })

        # Print table
        print(f"\n{'Strategy':<12} {'MRR':>8} {'Chunks':>8} {'Efficiency':>12} {'Est.Cost':>10}")
        print("-" * 55)
        for a in analysis:
            print(
                f"{a['strategy']:<12} {a['mrr']:>8.3f} {a['chunks']:>8} "
                f"{a['efficiency_score']:>12.3f} {a['estimated_cost']:>10}"
            )

        # Decision matrix with different priorities
        print("\n--- Decision Matrix (Weighted Scores) ---")
        print("We assume normalized MRR and inverted chunk count (fewer = better).")
        print("Quality weight = 0.7, Efficiency weight = 0.3")
        print(f"{'Strategy':<12} {'Quality (0.7)':>15} {'Efficiency (0.3)':>18} {'Total Score':>12}")
        print("-" * 60)

        max_mrr = max(a["mrr"] for a in analysis) or 1
        max_eff = max(a["efficiency_score"] for a in analysis) or 1

        for a in analysis:
            norm_mrr = a["mrr"] / max_mrr
            norm_eff = a["efficiency_score"] / max_eff
            total = 0.7 * norm_mrr + 0.3 * norm_eff
            a["total_score"] = round(total, 3)
            print(
                f"{a['strategy']:<12} {norm_mrr:>15.3f} {norm_eff:>18.3f} {total:>12.3f}"
            )

        # Return enriched data
        return {"analysis": analysis}


if __name__ == "__main__":
    # Run benchmark
    benchmark = ChunkingBenchmark(
        embedding_model="all-MiniLM-L6-v2",
        chunks_dir="data/chunks",
        queries_path="src/evaluation/queries.json",
        results_path="data/chunks/benchmark_results.json",
    )
    results = benchmark.run_full_benchmark()

    # Generate advanced analysis
    analysis = ChunkingBenchmark.generate_analysis_report(results)

    # Optionally save analysis
    analysis_path = Path("data/chunks/analysis.json")
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    print(f"\nAnalysis saved to: {analysis_path}")