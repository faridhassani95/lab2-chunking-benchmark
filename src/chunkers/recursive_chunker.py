"""
Recursive Character Chunker — Separator-aware chunking strategy.

Splits text using a hierarchy of separators:
Paragraph (double newline) → Sentence → Line → Word → Character

Preserves semantic boundaries better than fixed-size chunking.
"""

from pathlib import Path
from typing import List, Dict, Optional
import json
import re


class RecursiveChunker:
    """
    Recursive text splitter using separator hierarchy.

    Args:
        chunk_size: Target characters per chunk (default: 1000)
        overlap: Overlapping characters between chunks (default: 200)
        separators: Ordered list of separators to try (default: paragraph, sentence, line, space, char)
    """

    def __init__(
        self,
        chunk_size: int = 1000,
        overlap: int = 200,
        separators: Optional[List[str]] = None,
    ):
        if overlap >= chunk_size:
            raise ValueError(f"Overlap ({overlap}) must be smaller than chunk_size ({chunk_size})")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]
        self.name = "recursive"

    def _split_by_separator(self, text: str, separator: str) -> List[str]:
        """Split text by separator, keeping separators attached to preceding text."""
        if separator == "":
            return list(text)
        
        parts = text.split(separator)
        # Re-attach separator to each part except the last
        return [p + separator for p in parts[:-1]] + [parts[-1]] if len(parts) > 1 else parts

    def _recursive_split(self, texts: List[str], separator_idx: int) -> List[str]:
        """
        Recursively split texts using separator hierarchy.
        Stops when chunks fit within chunk_size or we run out of separators.
        """
        if separator_idx >= len(self.separators):
            return texts

        separator = self.separators[separator_idx]
        result = []

        for text in texts:
            if len(text) <= self.chunk_size:
                result.append(text)
            else:
                splits = self._split_by_separator(text, separator)
                # Filter out empty strings
                splits = [s for s in splits if s]
                result.extend(self._recursive_split(splits, separator_idx + 1))

        return result

    def _merge_with_overlap(self, splits: List[str]) -> List[str]:
        """Merge splits into chunks with target size and overlap."""
        if not splits:
            return []

        chunks = []
        current = ""
        
        for split in splits:
            if len(current) + len(split) <= self.chunk_size:
                current += split
            else:
                if current:
                    chunks.append(current)
                # Start new chunk with overlap from previous
                if chunks and self.overlap > 0:
                    prev = chunks[-1]
                    overlap_text = prev[-self.overlap:] if len(prev) >= self.overlap else prev
                    current = overlap_text + split
                else:
                    current = split

        if current:
            chunks.append(current)

        return chunks

    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Split text into chunks using recursive separator strategy.

        Args:
            text: Input text
            metadata: Optional dict with source info

        Returns:
            List of chunk dicts
        """
        if not text or not text.strip():
            return []

        # First, split recursively using separator hierarchy
        splits = self._recursive_split([text], separator_idx=0)

        # Then merge with overlap to reach target size
        merged = self._merge_with_overlap(splits)

        # Build chunk records
        chunks = []
        for i, chunk_text in enumerate(merged):
            chunks.append({
                "chunk_id": f"{metadata.get('source', 'doc')}_{self.name}_{i:04d}",
                "text": chunk_text,
                "char_count": len(chunk_text),
                "metadata": metadata or {},
                "strategy": self.name,
            })

        return chunks

    def chunk_directory(self, input_dir: Path, output_dir: Path) -> Dict:
        """
        Chunk all .md files in input_dir, save to output_dir.

        Args:
            input_dir: Path to cleaned .md files
            output_dir: Path to save chunked JSON

        Returns:
            Statistics dict
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
        
        stats_file = output_dir / f"stats_{self.name}.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        print(f"✅ Recursive Chunker done:")
        print(f"   {stats['total_chunks']} chunks from {stats['files_processed']} files")
        print(f"   Avg chunk: {stats['avg_chunk_size']:.0f} chars")
        print(f"   Output: {chunks_file}")

        return stats


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    input_dir = PROJECT_ROOT / "data/processed/java_docs/final"
    output_dir = PROJECT_ROOT / "data/chunks"

    chunker = RecursiveChunker(chunk_size=1000, overlap=200)
    stats = chunker.chunk_directory(input_dir, output_dir)