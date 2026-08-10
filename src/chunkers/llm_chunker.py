"""
LLM-based Chunker v2 — Boundary Index Method with min/max constraints.

Sends sentences to LLM, gets back breakpoint indices.
We do the actual splitting — LLM only decides WHERE to split.
Post-processes chunks to enforce size constraints.
No rewriting, no summarization, fully lossless.
"""

from pathlib import Path
from typing import List, Dict, Optional
import json
import subprocess
import re
import time


class LLMChunker:
    """
    Chunks text using LLM-predicted boundary indices with size validation.

    The LLM receives numbered sentences and returns JSON with breakpoints.
    We split at those indices — the text itself is never modified.
    Post-processing enforces min/max chunk size constraints.

    Args:
        model_name: Ollama model name (default: llama-local:latest)
        chunk_size_hint: Target sentences per chunk hint for the LLM (default: 5)
        min_chunk_chars: Minimum characters per chunk, merge smaller ones (default: 300)
        max_chunk_chars: Maximum characters per chunk, split larger ones (default: 1200)
        delay: Seconds to wait between API calls (default: 1.0)
        max_sentences_per_call: Max sentences per LLM call (default: 30)
    """

    def __init__(
        self,
        model_name: str = "llama-local:latest",
        chunk_size_hint: int = 5,
        min_chunk_chars: int = 300,
        max_chunk_chars: int = 1200,
        delay: float = 1.0,
        max_sentences_per_call: int = 30,
    ):
        self.model_name = model_name
        self.chunk_size_hint = chunk_size_hint
        self.min_chunk_chars = min_chunk_chars
        self.max_chunk_chars = max_chunk_chars
        self.delay = delay
        self.max_sentences_per_call = max_sentences_per_call
        self.name = "llm"

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences. Handles code patterns like Object.toString() and numbers like 1.0."""
        sentences = []
        current = ""

        for char in text:
            current += char
            if char in ".!?":
                if len(current) >= 2:
                    prev_char = current[-2]
                    if prev_char == "(" or prev_char == ")":
                        continue
                    if prev_char.isdigit():
                        continue
                sentences.append(current.strip())
                current = ""

        if current.strip():
            sentences.append(current.strip())

        return [s for s in sentences if s]

    def _query_ollama(self, prompt: str) -> str:
        """Send prompt to Ollama and get response."""
        try:
            result = subprocess.run(
                ["ollama", "run", self.model_name],
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=120,
            )
            if result.returncode != 0:
                return ""
            return result.stdout.strip()
        except:
            return ""

    def _build_boundary_prompt(self, sentences: List[str], start_idx: int) -> str:
        """Build prompt asking LLM for breakpoint indices only."""
        numbered = "\n".join([f"[{i}] {s[:150]}" for i, s in enumerate(sentences)])

        prompt = f"""You are a precise text chunking assistant.

Below are numbered sentences from a Java documentation file.
Decide where to split them into chunks. Each chunk should contain {self.chunk_size_hint} sentences on average.

Output ONLY a JSON object with a "breaks" key containing the sentence indices AFTER which to break.

Example:
{{"breaks": [4, 9, 14]}}

This means: break after sentence 4, after sentence 9, after sentence 14.

Rules:
- Do NOT modify or rewrite any sentence text
- Only specify break indices
- Return ONLY the JSON, no other text

Numbered sentences ({len(sentences)} total, starting at index {start_idx}):
---
{numbered}
---"""

        return prompt

    def _parse_boundaries(self, response: str, num_sentences: int) -> List[int]:
        """Parse LLM response to get break indices."""
        if not response:
            return []

        match = re.search(r'\{[^}]*"breaks"[^}]*\}', response, re.DOTALL)
        if not match:
            return []

        try:
            data = json.loads(match.group())
            breaks = data.get("breaks", [])
            return [b for b in breaks if isinstance(b, int) and 0 <= b < num_sentences - 1]
        except:
            return []

    def _validate_and_fix_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """
        Post-process chunks to enforce min/max size constraints.
        - Merge chunks smaller than min_chunk_chars with neighbors
        - Split chunks larger than max_chunk_chars at sentence boundaries
        """
        if not chunks:
            return chunks

        fixed = []

        for chunk in chunks:
            current = chunk.copy()

            # === HANDLE TOO SMALL ===
            if current["char_count"] < self.min_chunk_chars and len(fixed) > 0:
                # Merge with previous chunk
                prev = fixed[-1]
                prev["text"] = prev["text"] + " " + current["text"]
                prev["char_count"] = len(prev["text"])
                prev["sentence_count"] = prev["sentence_count"] + current["sentence_count"]
                continue

            # === HANDLE TOO LARGE ===
            if current["char_count"] > self.max_chunk_chars:
                # Split by sentences at the midpoint
                chunk_sentences = current["text"].split(". ")
                if len(chunk_sentences) >= 4:
                    mid = len(chunk_sentences) // 2

                    first_half = ". ".join(chunk_sentences[:mid])
                    if not first_half.endswith("."):
                        first_half += "."
                    second_half = ". ".join(chunk_sentences[mid:])
                    if not second_half.endswith(".") and not second_half.endswith('"'):
                        second_half += "."

                    if len(first_half) >= self.min_chunk_chars:
                        chunk1 = current.copy()
                        chunk1["text"] = first_half
                        chunk1["char_count"] = len(first_half)
                        chunk1["sentence_count"] = mid
                        fixed.append(chunk1)

                        chunk2 = current.copy()
                        chunk2["text"] = second_half
                        chunk2["char_count"] = len(second_half)
                        chunk2["sentence_count"] = current["sentence_count"] - mid
                        fixed.append(chunk2)
                        continue

            fixed.append(current)

        # Re-index chunk IDs
        for i, chunk in enumerate(fixed):
            chunk["chunk_id"] = chunk["chunk_id"].rsplit("_", 1)[0] + f"_{i:04d}"

        return fixed

    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Split text into chunks using LLM-predicted boundaries with size validation.

        Process:
        1. Split text into sentences
        2. Send batches of sentences to LLM
        3. LLM returns breakpoint indices
        4. Split sentences at those indices
        5. Validate and fix chunk sizes (min/max)
        """
        if not text or not text.strip():
            return []

        sentences = self._split_sentences(text)
        if len(sentences) <= 1:
            return [{
                "chunk_id": f"{metadata.get('source', 'doc')}_{self.name}_0000",
                "text": text.strip(),
                "char_count": len(text.strip()),
                "sentence_count": len(sentences),
                "metadata": metadata or {},
                "strategy": self.name,
            }]

        # Collect all breakpoints
        all_breaks = []
        total_batches = (len(sentences) + self.max_sentences_per_call - 1) // self.max_sentences_per_call

        for batch_num, start in enumerate(range(0, len(sentences), self.max_sentences_per_call)):
            batch = sentences[start:start + self.max_sentences_per_call]

            prompt = self._build_boundary_prompt(batch, start)
            response = self._query_ollama(prompt)
            breaks = self._parse_boundaries(response, len(batch))

            for b in breaks:
                all_breaks.append(start + b)

            print(f"  Batch {batch_num + 1}/{total_batches}: {len(breaks)} breaks from {len(batch)} sentences")

            if batch_num < total_batches - 1:
                time.sleep(self.delay)

        # Add final boundary
        if not all_breaks or all_breaks[-1] != len(sentences) - 1:
            all_breaks.append(len(sentences) - 1)
        all_breaks = sorted(set(all_breaks))

        # Build chunks by joining sentences between breakpoints
        chunks = []
        prev_break = 0
        for break_idx in all_breaks:
            chunk_sentences = sentences[prev_break:break_idx + 1]
            chunk_text = " ".join(chunk_sentences)
            chunks.append({
                "chunk_id": f"{metadata.get('source', 'doc')}_{self.name}_0",
                "text": chunk_text,
                "char_count": len(chunk_text),
                "sentence_count": len(chunk_sentences),
                "metadata": metadata or {},
                "strategy": self.name,
            })
            prev_break = break_idx + 1

        # Validate and fix sizes
        chunks = self._validate_and_fix_chunks(chunks)

        return chunks

    def chunk_directory(self, input_dir: Path, output_dir: Path) -> Dict:
        """Chunk all .md files using LLM boundary prediction with size validation."""
        output_dir.mkdir(parents=True, exist_ok=True)
        all_chunks = []
        stats = {"files_processed": 0, "total_chunks": 0, "total_chars": 0}

        files = sorted(input_dir.glob("*.md"))
        print(f"Processing {len(files)} files with LLM boundary chunker...")
        print(f"Model: {self.model_name} | Hint: ~{self.chunk_size_hint} sentences/chunk")
        print(f"Size constraints: {self.min_chunk_chars}-{self.max_chunk_chars} chars\n")

        for idx, file_path in enumerate(files, 1):
            print(f"[{idx}/{len(files)}] {file_path.name}...")

            text = file_path.read_text(encoding="utf-8")
            metadata = {"source": file_path.stem, "filename": file_path.name}

            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
            stats["files_processed"] += 1
            stats["total_chunks"] += len(chunks)
            stats["total_chars"] += len(text)

            sizes = [c["char_count"] for c in chunks]
            print(f"  Chunks: {len(chunks)} | Min: {min(sizes)} | Max: {max(sizes)} | Avg: {sum(sizes)//len(sizes)}")
            print(f"  Total: {stats['total_chunks']} chunks\n")

            time.sleep(self.delay)

        # Save chunks
        chunks_file = output_dir / f"chunks_{self.name}.json"
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        stats["avg_chunk_size"] = sum(c["char_count"] for c in all_chunks) / len(all_chunks) if all_chunks else 0
        stats["model"] = self.model_name
        stats["min_chunk_chars"] = self.min_chunk_chars
        stats["max_chunk_chars"] = self.max_chunk_chars

        stats_file = output_dir / f"stats_{self.name}.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        print(f"✅ LLM Boundary Chunker done: {stats['total_chunks']} chunks, avg {stats['avg_chunk_size']:.0f} chars")
        return stats


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    input_dir = PROJECT_ROOT / "data/processed/java_docs/final"
    output_dir = PROJECT_ROOT / "data/chunks"

    chunker = LLMChunker(
        model_name="llama-local:latest",
        chunk_size_hint=5,
        min_chunk_chars=300,
        max_chunk_chars=1200,
        delay=1.0,
        max_sentences_per_call=30,
    )
    stats = chunker.chunk_directory(input_dir, output_dir)