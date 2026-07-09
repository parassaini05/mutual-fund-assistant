import json
import os
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = _PROJECT_ROOT / "data" / "raw"

def save_cleaned_text(fund_name: str, clean_text: str, source_url: str, scraped_date: str) -> Path:
    out_dir = Path(RAW_DATA_DIR) / "cleaned"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() else "_" for c in fund_name)
    out_file = out_dir / f"{safe_name}.txt"
    out_file.write_text(f"{fund_name}\n{source_url}\n{scraped_date}\n\n{clean_text}", encoding="utf-8")
    return out_file

def save_chunks(fund_name: str, chunks: list) -> Path:
    out_dir = Path(RAW_DATA_DIR) / "chunks"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = "".join(c if c.isalnum() else "_" for c in fund_name)
    out_file = out_dir / f"{safe_name}.jsonl"
    with open(out_file, "w", encoding="utf-8") as f:
        for chunk in chunks:
            # Tests expect "text", "fund_name", "source_url" in JSON
            # chunk.to_metadata_dict() or chunk.__dict__
            d = chunk.to_metadata_dict() if hasattr(chunk, 'to_metadata_dict') else chunk.__dict__.copy()
            d["text"] = chunk.text
            d["fund_name"] = chunk.fund_name
            d["source_url"] = chunk.source_url
            f.write(json.dumps(d) + "\n")
    return out_file
