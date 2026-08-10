"""
Character Chunker — Fixed-size baseline chunking strategy.

Splits text into chunks of N characters with configurable overlap.
No understanding of language or structure — pure baseline.
"""

from pathlib import Path
from typing import List, Dict, Optional
import json


class CharacterChunker:
    """
    Fixed-size character chunker with overlap.

    Args:
        chunk_size: Characters per chunk (default: 1000)
        overlap: Overlapping characters between consecutive chunks (default: 200)
    """

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        if overlap >= chunk_size:
            raise ValueError(f"Overlap ({overlap}) must be smaller than chunk_size ({chunk_size})")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.name = "character"

    def chunk_text(self, text: str, metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Split text into fixed-size character chunks.

        Args:
            text: Input text
            metadata: Optional dict with source info

        Returns:
            List of chunk dicts with id, text, char_count, metadata
        """
        if not text or not text.strip():
            return []

        chunks = []
        start = 0
        index = 0

        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            chunk_text = text[start:end]

            chunks.append({
                "chunk_id": f"{metadata.get('source', 'doc')}_{self.name}_{index:04d}",
                "text": chunk_text,
                "char_count": len(chunk_text),
                "start_char": start,
                "end_char": end,
                "metadata": metadata or {},
                "strategy": self.name,
            })

            start += self.chunk_size - self.overlap
            index += 1

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

        print(f"✅ Character Chunker done:")
        print(f"   {stats['total_chunks']} chunks from {stats['files_processed']} files")
        print(f"   Avg chunk: {stats['avg_chunk_size']:.0f} chars")
        print(f"   Output: {chunks_file}")

        return stats


if __name__ == "__main__":
    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    input_dir = PROJECT_ROOT / "data/processed/java_docs/final"
    output_dir = PROJECT_ROOT / "data/chunks"

    chunker = CharacterChunker(chunk_size=1000, overlap=200)
    stats = chunker.chunk_directory(input_dir, output_dir)