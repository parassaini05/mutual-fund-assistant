"""
ingestion/chunker.py — Phase 2.4 (v2): Section-aware text chunker for the RAG pipeline.

Splits the cleaned plain text from a ScrapedPage into token-aware chunks
with configurable size and overlap. Includes a noise-stripping pre-pass
that removes Groww-specific boilerplate before chunking.
"""

import hashlib
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("chunker")

# ── Project imports ────────────────────────────────────────────────────────
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import CHUNK_SIZE, CHUNK_OVERLAP, MIN_CHUNK_TOKENS

# ── Tokeniser setup ────────────────────────────────────────────────────────

def _build_tokeniser():
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        logger.info("Tokeniser: tiktoken (cl100k_base) loaded.")

        def encode(text: str) -> list[int]:
            return enc.encode(text)

        def decode(tokens: list[int]) -> str:
            return enc.decode(tokens)

        return encode, decode, "tiktoken"

    except ImportError:
        logger.warning(
            "tiktoken not found. Falling back to word-count approximation. "
            "Install tiktoken for accurate token counts: pip install tiktoken"
        )

        def encode(text: str) -> list[int]:
            words = text.split()
            return list(range(len(words)))

        def decode(tokens: list[int]) -> str:
            raise NotImplementedError(
                "Word-count tokeniser does not support decoding."
            )

        return encode, decode, "word-count"


_ENCODE, _DECODE, _TOKENISER_NAME = _build_tokeniser()


# ── Data model ─────────────────────────────────────────────────────────────

@dataclass
class Chunk:
    text: str
    token_count: int
    chunk_index: int
    chunk_hash: str
    chunk_type: str          # 'facts', 'faq', 'returns', 'general'
    source_url: str
    fund_name: str
    amc: str
    category: str
    scraped_date: str

    def to_metadata_dict(self) -> dict:
        """Return metadata as a plain dict (used by vector_store.py)."""
        return {
            "source_url": self.source_url,
            "fund_name": self.fund_name,
            "amc": self.amc,
            "category": self.category,
            "scraped_date": self.scraped_date,
            "chunk_index": self.chunk_index,
            "chunk_type": self.chunk_type,
            "token_count": self.token_count,
            "chunk_hash": self.chunk_hash,
            "text": self.text,
        }


# ── Internal helpers ────────────────────────────────────────────────────────

def _md5(text: str) -> str:
    """Return the MD5 hex digest of the given text."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _count_tokens(text: str) -> int:
    """Return the token count for a text string using the active tokeniser."""
    return len(_ENCODE(text))


# ── Noise-stripping pre-pass ────────────────────────────────────────────────

_NOISE_START_MARKERS = [
    "invest in stocks",
    "holdings (",
    "compare similar funds",
    "vaishnavi tech park",
    "mf screener",
]

_SECTION_TAGS = [
    (re.compile(r"nav:|min\.? for sip|fund size|expense ratio|exit load", re.I), "facts"),
    (re.compile(r"^(how|what|why|when|can i|is there|which|who)", re.I),          "faq"),
    (re.compile(r"returns?|annualised|rank\s*\(", re.I),                           "returns"),
    (re.compile(r"fund manager|investment objective|about .+fund", re.I),          "about"),
]


def _strip_noise_sections(text: str, fund_name: str) -> str:
    lines = text.splitlines()
    clean_lines: list[str] = []
    skipping = False
    past_header = False
    fund_name_lower = fund_name.lower().replace(" - direct growth", "").replace(" direct growth", "")

    for line in lines:
        stripped = line.strip()
        low = stripped.lower()

        if not past_header:
            if "ctrl+k" in low or fund_name_lower in low:
                past_header = True
                if "ctrl+k" not in low:
                    clean_lines.append(stripped)
            elif stripped.startswith("#") or stripped.startswith("===="):
                clean_lines.append(stripped)
            continue

        if not skipping:
            for marker in _NOISE_START_MARKERS:
                if marker in low:
                    skipping = True
                    break

        if skipping:
            if re.match(r"^(how|what|why|when|can i|is there|which|who|about )", low):
                skipping = False
                clean_lines.append(stripped)
            elif "vaishnavi tech park" in low or "mf screener" in low:
                break
            continue

        clean_lines.append(stripped)

    result = "\n".join(clean_lines)
    return result


def _tag_chunk_type(text: str) -> str:
    for pattern, tag in _SECTION_TAGS:
        if pattern.search(text):
            return tag
    return "general"


def _split_into_sentences(text: str) -> list[str]:
    text = text.replace("\n\n", " <PARA> ")
    text = text.replace("\n", " <NL> ")
    sentence_pattern = re.compile(r"(?<=[.!?])\s+")
    raw_sentences = sentence_pattern.split(text)

    sentences: list[str] = []
    for sent in raw_sentences:
        parts = re.split(r"<PARA>|<NL>", sent)
        for part in parts:
            part = part.strip()
            if part:
                sentences.append(part)

    return sentences


def _sentences_to_token_chunks(
    sentences: list[str],
    chunk_size: int,
    chunk_overlap: int,
    min_tokens: int,
) -> list[str]:
    chunks: list[str] = []
    current_sentences: list[str] = []
    current_tokens: int = 0

    for sentence in sentences:
        sent_tokens = _count_tokens(sentence)

        if sent_tokens > chunk_size:
            if current_sentences:
                chunk_text = " ".join(current_sentences).strip()
                if _count_tokens(chunk_text) >= min_tokens:
                    chunks.append(chunk_text)
                current_sentences = []
                current_tokens = 0
            if sent_tokens >= min_tokens:
                chunks.append(sentence)
            continue

        if current_tokens + sent_tokens > chunk_size and current_sentences:
            chunk_text = " ".join(current_sentences).strip()
            if _count_tokens(chunk_text) >= min_tokens:
                chunks.append(chunk_text)

            overlap_sentences: list[str] = []
            overlap_tokens: int = 0
            for prev_sent in reversed(current_sentences):
                prev_tokens = _count_tokens(prev_sent)
                if overlap_tokens + prev_tokens <= chunk_overlap:
                    overlap_sentences.insert(0, prev_sent)
                    overlap_tokens += prev_tokens
                else:
                    break

            current_sentences = overlap_sentences
            current_tokens = overlap_tokens

        current_sentences.append(sentence)
        current_tokens += sent_tokens

    if current_sentences:
        chunk_text = " ".join(current_sentences).strip()
        if _count_tokens(chunk_text) >= min_tokens:
            chunks.append(chunk_text)

    return chunks


# ── Public API ──────────────────────────────────────────────────────────────

def chunk_text(
    text: str,
    source_url: str,
    fund_name: str,
    amc: str,
    category: str,
    scraped_date: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    min_tokens: int = MIN_CHUNK_TOKENS,
) -> list[Chunk]:
    if not text or not text.strip():
        logger.warning(f"  Empty text passed to chunker for '{fund_name}'. No chunks.")
        return []

    logger.info(
        f"Chunking '{fund_name}' | "
        f"size={chunk_size} tok | overlap={chunk_overlap} tok | "
        f"tokeniser={_TOKENISER_NAME}"
    )

    text = _strip_noise_sections(text, fund_name)
    sentences = _split_into_sentences(text)
    raw_chunks = _sentences_to_token_chunks(
        sentences, chunk_size, chunk_overlap, min_tokens
    )

    prefix = f"[{fund_name}] "
    seen_hashes: set[str] = set()
    chunks: list[Chunk] = []
    discarded_empty = 0
    discarded_dupe = 0

    for idx, chunk_text_str in enumerate(raw_chunks):
        token_count = _count_tokens(chunk_text_str)

        if token_count < min_tokens:
            discarded_empty += 1
            continue

        chunk_hash = _md5(chunk_text_str)
        if chunk_hash in seen_hashes:
            discarded_dupe += 1
            continue
        seen_hashes.add(chunk_hash)

        prefixed_text = prefix + chunk_text_str
        chunk_type = _tag_chunk_type(chunk_text_str)

        chunks.append(
            Chunk(
                text=prefixed_text,
                token_count=_count_tokens(prefixed_text),
                chunk_index=len(chunks),
                chunk_hash=chunk_hash,
                chunk_type=chunk_type,
                source_url=source_url,
                fund_name=fund_name,
                amc=amc,
                category=category,
                scraped_date=scraped_date,
            )
        )

    logger.info(
        f"  Chunks created: {len(chunks)} | "
        f"discarded (too small): {discarded_empty} | "
        f"discarded (duplicate): {discarded_dupe}"
    )

    if chunks:
        token_counts = [c.token_count for c in chunks]
        min_t, max_t, avg_t = min(token_counts), max(token_counts), sum(token_counts) / len(token_counts)
        out_of_range = sum(1 for t in token_counts if t < 300 or t > 550)
        logger.info(
            f"  Token stats - min: {min_t} | max: {max_t} | avg: {avg_t:.0f} | "
            f"out-of-range (300-550): {out_of_range}/{len(chunks)}"
        )

    return chunks


def chunk_page(scraped_page) -> list[Chunk]:
    return chunk_text(
        text=scraped_page.raw_text,
        source_url=scraped_page.source_url,
        fund_name=scraped_page.fund_name,
        amc=scraped_page.amc,
        category=scraped_page.category,
        scraped_date=scraped_page.scraped_date,
    )
