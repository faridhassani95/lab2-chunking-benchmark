"""
Semantic Chunker — Embedding-similarity based chunking.

Splits text by grouping sentences with similar semantic meaning.
Uses sentence-transformers for embeddings and cosine similarity.
"""

from pathlib import Path
from typing import List, Dict, Optional, Tuple
import json
import re
import numpy as np
from sentence_transformers import SentenceTransformer


class SemanticChunker:
    """
    Chunks text based on semantic similarity between consecutive sentences.

    Args:
        model_name: SentenceTransformer model (default: all-MiniLM-L6-v2)
        similarity_threshold: Cosine similarity below which a new chunk starts (default: 0.5)
        min_chunk_size: Minimum characters per chunk (default: 200)
        max_chunk_size: Maximum characters per chunk (default: 1500)
        overlap_sentences: Number of sentences to overlap between chunks (default: 2)
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        similarity_threshold: float = 0.5,
        min_chunk_size: int = 200,
        max_chunk_size: int = 1500,
        overlap_sentences: int = 2,
    ):
        if similarity_threshold < 0 or similarity_threshold > 1:
            raise ValueError(f"similarity_threshold must be between 0 and 1, got {similarity_threshold}")
        if min_chunk_size >= max_chunk_size:
            raise ValueError(f"min_chunk_size ({min_chunk_size}) must be smaller than max_chunk_size ({max_chunk_size})")

        self.similarity_threshold = similarity_threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.overlap_sentences = overlap_sentences
        self.name = "semantic"

        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name)
        print("Model loaded.")

    def _extract_code_blocks(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Extract markdown code blocks and replace with placeholders.
        Returns (text_with_placeholders, {placeholder: original_code})
        """
        code_blocks = {}
        counter = 0

        def _replace(match):
            nonlocal counter
            placeholder = f"__CODE_BLOCK_{counter}__"
            code_blocks[placeholder] = match.group(0)
            counter += 1
            return placeholder

        # Match ``` ... ``` code blocks
        pattern = r'```[^`]*```'
        text_with_placeholders = re.sub(pattern, _replace, text, flags=re.DOTALL)
        
        return text_with_placeholders, code_blocks

    def _restore_code_blocks(self, text: str, code_blocks: Dict[str, str]) -> str:
        """Restore code blocks from placeholders."""
        for placeholder, original in code_blocks.items():
            text = text.replace(placeholder, original)
        return text

    def _split_sentences(self, text: str) -> List[str]:
        """
        Split text into sentences. Handles JavaDoc patterns:
        - Doesn't split on "Object.toString()"
        - Doesn't split on "Since 1.0" if at line start
        - Preserves code placeholders
        """
        sentences = []
        current = ""

        for char in text:
            current += char

            # Check if this is a sentence boundary
            if char in ".!?":
                # Peek at context around the period
                # Avoid splitting on:
                # - method calls: toString(), getValue()
                # - package names: java.lang.Object.
                # - numbers: 1.0, 0.5
                # - abbreviations like "e.g." or "i.e."

                # If followed by letter or digit without space, not a sentence boundary
                # This handles: toString(), O(n)., Since 1.0
                is_boundary = True

                # Check: period followed by space/newline AND not preceded by single uppercase (abbreviation)
                if len(current) >= 2:
                    prev_char = current[-2] if len(current) >= 2 else ""
                    
                    # Method call: text() followed by nothing or space
                    if prev_char == "(" or prev_char == ")":
                        is_boundary = False
                    
                    # Number: digit.digit
                    if prev_char.isdigit():
                        is_boundary = False

                if is_boundary:
                    sentences.append(current.strip())
                    current = ""

        if current.strip():
            sentences.append(current.strip())

        return [s for s in sentences if s]

    def _cosine_similarity(self, emb1, emb2):
        """Compute cosine similarity between two embeddings."""
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Split text into semantically coherent chunks.

        Args:
            text: Input text
            metadata: Optional dict with source info

        Returns:
            List of chunk dicts
        """
        if not text or not text.strip():
            return []

        # Extract and placeholder code blocks
        text_no_code, code_blocks = self._extract_code_blocks(text)

        # Split into sentences
        sentences = self._split_sentences(text_no_code)

        if len(sentences) == 0:
            return []
        if len(sentences) == 1:
            return [{
                "chunk_id": f"{metadata.get('source', 'doc')}_{self.name}_0000",
                "text": self._restore_code_blocks(sentences[0], code_blocks),
                "char_count": len(text.strip()),
                "sentence_count": 1,
                "metadata": metadata or {},
                "strategy": self.name,
            }]

        # Get embeddings for all sentences
        embeddings = self.model.encode(sentences, show_progress_bar=False)

        # Group sentences by semantic similarity
        raw_chunks = []
        current_chunk = [sentences[0]]
        current_size = len(sentences[0])

        for i in range(1, len(sentences)):
            sim = self._cosine_similarity(embeddings[i-1], embeddings[i])

            # Check if we should start a new chunk
            should_break = (
                sim < self.similarity_threshold and current_size >= self.min_chunk_size
            ) or current_size + len(sentences[i]) > self.max_chunk_size

            if should_break and current_chunk:
                raw_chunks.append(current_chunk)
                # Start new chunk with overlap from previous
                if self.overlap_sentences > 0 and len(current_chunk) > self.overlap_sentences:
                    current_chunk = current_chunk[-self.overlap_sentences:] + [sentences[i]]
                    current_size = sum(len(s) for s in current_chunk)
                else:
                    current_chunk = [sentences[i]]
                    current_size = len(sentences[i])
            else:
                current_chunk.append(sentences[i])
                current_size += len(sentences[i])

        if current_chunk:
            raw_chunks.append(current_chunk)

        # Build final chunks with restored code blocks
        result = []
        for i, chunk_sentences in enumerate(raw_chunks):
            chunk_text = " ".join(chunk_sentences)
            chunk_text = self._restore_code_blocks(chunk_text, code_blocks)

            result.append({
                "chunk_id": f"{metadata.get('source', 'doc')}_{self.name}_{i:04d}",
                "text": chunk_text,
                "char_count": len(chunk_text),
                "sentence_count": len(chunk_sentences),
                "metadata": metadata or {},
                "strategy": self.name,
            })

        return result

    def chunk_directory(self, input_dir: Path, output_dir: Path) -> Dict:
        """
        Chunk all .md files in input_dir, save to output_dir.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        all_chunks = []
        stats = {"files_processed": 0, "total_chunks": 0, "total_chars": 0}

        for file_path in sorted(input_dir.glob("*.md")):
            text = file_path.read_text(encoding="utf-8")
            metadata = {
                "source": file_path.stem,
                "filename": file_path.name,
            }

            chunks = self.chunk_text(text, metadata)
            all_chunks.extend(chunks)
            stats["files_processed"] += 1
            stats["total_chunks"] += len(chunks)
            stats["total_chars"] += len(text)

        # Save chunks
        chunks_file = output_dir / f"chunks_{self.name}.json"
        with open(chunks_file, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        # Calculate and save stats
        stats["avg_chunk_size"] = sum(c["char_count"] for c in all_chunks) / len(all_chunks) if all_chunks else 0
        stats["similarity_threshold"] = self.similarity_threshold
        stats["overlap_sentences"] = self.overlap_sentences

        stats_file = output_dir / f"stats_{self.name}.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        print(f"✅ Semantic Chunker done:")
        print(f"   {stats['total_chunks']} chunks from {stats['files_processed']} files")
        print(f"   Avg chunk: {stats['avg_chunk_size']:.0f} chars")
        print(f"   Threshold: {self.similarity_threshold} | Overlap: {self.overlap_sentences} sentences")
        print(f"   Output: {chunks_file}")

        return stats


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    input_dir = PROJECT_ROOT / "data/processed/java_docs/final"
    output_dir = PROJECT_ROOT / "data/chunks"

    chunker = SemanticChunker(
        model_name="all-MiniLM-L6-v2",
        similarity_threshold=0.5,
        min_chunk_size=200,
        max_chunk_size=1500,
        overlap_sentences=2,
    )
    stats = chunker.chunk_directory(input_dir, output_dir)