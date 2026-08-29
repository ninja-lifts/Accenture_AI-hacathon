"""Stage 05 - Retrieve.

Hybrid BM25 + embeddings over the redacted document index. Two filters
applied BEFORE scoring, not after:
  1. Entitlement - documents the principal may not read never enter the pool.
  2. Window - a document well outside the movement window is not evidence for
     it, however well it matches on keywords. This is the first line of
     defence against SC-08's decoys; Stage 06's falsification tests (which
     find no supporting statistical signal for any of them) are the second -
     defence in depth rather than relying on either alone."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

from engine import redaction
from engine.telemetry import stage

WINDOW_LOOKBACK_DAYS = 14
WINDOW_LOOKAHEAD_DAYS = 3
TOP_N = 6
BM25_WEIGHT = 0.5

_INDEX_CACHE: dict[str, Any] = {}


def _load_index(documents_path: str) -> dict[str, Any]:
    if documents_path in _INDEX_CACHE:
        return _INDEX_CACHE[documents_path]

    docs = []
    with open(documents_path, encoding="utf-8") as fh:
        for line in fh:
            docs.append(json.loads(line))

    corpus_tokens = []
    n_redactions = []
    embed_texts = []
    for d in docs:
        text = f"{d['title']}\n{d['body']}"
        redacted_text, n = redaction.redact(text)
        d["_redacted_text"] = redacted_text
        d["_n_redactions"] = n
        d["_injection_patterns"] = redaction.flag_injection(text)
        corpus_tokens.append(_tokenize(redacted_text))
        n_redactions.append(n)
        embed_texts.append(redacted_text)

    from rank_bm25 import BM25Okapi

    bm25 = BM25Okapi(corpus_tokens)

    embeddings = None
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2")
        embeddings = model.encode(embed_texts, show_progress_bar=False, normalize_embeddings=True)
    except Exception:  # noqa: BLE001 - no network / model unavailable: degrade to BM25-only
        model = None

    index = {"docs": docs, "bm25": bm25, "model": model, "embeddings": embeddings}
    _INDEX_CACHE[documents_path] = index
    return index


def _tokenize(text: str) -> list[str]:
    return [t for t in text.lower().replace("-", " ").split() if t.isalnum() or any(c.isalnum() for c in t)]


def _normalize(scores):
    import numpy as np

    scores = np.asarray(scores, dtype=float)
    lo, hi = scores.min(), scores.max()
    if hi - lo < 1e-9:
        return np.zeros_like(scores)
    return (scores - lo) / (hi - lo)


def _build_query(ctx: dict[str, Any]) -> str:
    kpi = ctx["contract"]["display_name"]
    segment = ctx.get("segment") or {}
    top = next((s for s in ctx.get("localization") or [] if not s["suppressed"]), None)
    dims = {**segment, **(top["dimensions"] if top else {})}
    parts = [kpi] + [str(v) for v in dims.values()] + ["decline", "issue", "cause"]
    return " ".join(parts)


def _entitled(doc: dict[str, Any], ctx: dict[str, Any]) -> bool:
    persona = ctx["persona"]
    if persona not in doc.get("visibility_roles", []):
        return False
    if persona == "category_manager":
        doc_category = doc.get("entities", {}).get("category")
        scoped_category = (ctx.get("segment") or {}).get("category")
        if doc_category and scoped_category and doc_category != scoped_category:
            return False
    return True


def _in_window(doc: dict[str, Any], focal_start: dt.date, focal_end: dt.date) -> bool:
    published = dt.datetime.fromisoformat(doc["published_at"].replace("Z", "+00:00")).date()
    lo = focal_start - dt.timedelta(days=WINDOW_LOOKBACK_DAYS)
    hi = focal_end + dt.timedelta(days=WINDOW_LOOKAHEAD_DAYS)
    return lo <= published <= hi


def run(ctx: dict[str, Any]) -> dict[str, Any]:
    with stage("05_retrieve", ctx["telemetry"]):
        settings = ctx["settings"]
        documents_path = str(Path(settings.data_dir) / "documents.jsonl")
        index = _load_index(documents_path)
        docs = index["docs"]

        window = ctx["window"]
        focal_start = dt.date.fromisoformat(window["focal_start"])
        focal_end = dt.date.fromisoformat(window["focal_end"])

        eligible_idx = [
            i for i, d in enumerate(docs)
            if _entitled(d, ctx) and _in_window(d, focal_start, focal_end)
        ]
        withheld = sum(1 for d in docs if not _entitled(d, ctx))
        ctx["security"]["documents_withheld"] += withheld

        if not eligible_idx:
            ctx["evidence"] = []
            return ctx

        query = _build_query(ctx)
        bm25_scores_all = index["bm25"].get_scores(_tokenize(query))
        bm25_scores = [bm25_scores_all[i] for i in eligible_idx]
        bm25_norm = _normalize(bm25_scores)

        if index["embeddings"] is not None and index["model"] is not None:
            import numpy as np

            q_emb = index["model"].encode([query], normalize_embeddings=True)[0]
            emb_sub = index["embeddings"][eligible_idx]
            cos = emb_sub @ q_emb
            cos_norm = _normalize(cos)
            final = BM25_WEIGHT * bm25_norm + (1 - BM25_WEIGHT) * cos_norm
        else:
            final = bm25_norm

        order = sorted(range(len(eligible_idx)), key=lambda k: final[k], reverse=True)[:TOP_N]

        evidence = []
        redactions_applied = 0
        injection_flags = []
        for k in order:
            i = eligible_idx[k]
            d = docs[i]
            flagged = bool(d["_injection_patterns"])
            if flagged:
                injection_flags.append(
                    {
                        "document_id": d["document_id"],
                        "pattern": d["_injection_patterns"][0],
                        "action_taken": "quoted_as_inert_evidence",
                    }
                )
            if d["_n_redactions"]:
                redactions_applied += d["_n_redactions"]
            evidence.append(
                {
                    "document_id": d["document_id"],
                    "source": d["source"],
                    "snippet": d["_redacted_text"][:400],
                    "retrieval_score": float(final[k]),
                    "published_at": d["published_at"],
                    "entitlement_ok": True,
                    "flagged_injection": flagged,
                }
            )

        ctx["evidence"] = evidence
        ctx["security"]["redactions_applied"] += redactions_applied
        ctx["security"]["injection_flags"].extend(injection_flags)

    return ctx
