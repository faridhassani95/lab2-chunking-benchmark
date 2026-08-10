from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
INPUT_DIR = PROJECT_ROOT / "data/processed/java_docs/documents"
OUTPUT_DIR = PROJECT_ROOT / "data/processed/java_docs/final"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def clean_document(text):
    text = text.replace("\u00a0", " ")
    text = text.replace("\xc2\xa0", " ")
    lines = text.splitlines()
    result = []
    skip_until_normal = False

    for i, line in enumerate(lines):
        line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)
        stripped = line.strip()

        if stripped.startswith("Module ") or stripped.startswith("Package "):
            continue
        if re.match(r'^([a-z_][a-z0-9_]*\.)+[A-Z][a-zA-Z0-9_]*(<[^>]*>)?$', stripped):
            continue
        if re.match(r'^[a-z_][a-z0-9_]*(\.[a-z_][a-z0-9_]*)+$', stripped):
            continue

        skip_triggers = [
            "All Implemented Interfaces:", "All Superinterfaces:",
            "Direct Known Subclasses:", "Type Parameters:",
            "Since:", "See Also:", "Implementation Note:",
            "See *Java Language Specification*:",
            "## Field Summary", "## Constructor Summary",
            "## Method Summary", "## Nested Class Summary",
            "## Enum Constant Summary",
        ]

        if stripped in skip_triggers:
            skip_until_normal = True
            continue
        if stripped.startswith("* ##"):
            skip_until_normal = True
            continue

        if skip_until_normal:
            if stripped == "" or stripped.startswith(":") or stripped.startswith("*") or stripped.startswith("-"):
                continue
            else:
                skip_until_normal = False
                if stripped in skip_triggers or stripped.startswith("* ##"):
                    skip_until_normal = True
                    continue

        if stripped == "---":
            continue
        if stripped.startswith("> "):
            line = line.replace("> ", "", 1)
        elif stripped.startswith(">"):
            line = line.replace(">", "", 1)

        replacements = {"&nbsp;": " ", "&lt;": "<", "&gt;": ">", "&amp;": "&", "&quot;": '"'}
        for k, v in replacements.items():
            line = line.replace(k, v)

        result.append(line)

    text = "\n".join(result)
    text = "\n".join(line.rstrip() for line in text.splitlines())
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def main():
    files = list(INPUT_DIR.glob("*.md"))
    print(f"Found {len(files)} documents\n")
    for file in files:
        raw_text = file.read_text(encoding="utf-8")
        cleaned = clean_document(raw_text)
        output_file = OUTPUT_DIR / file.name
        output_file.write_text(cleaned, encoding="utf-8")
        print(f"Cleaned: {file.name}")

if __name__ == "__main__":
    main()