"""complete()'s resumable-cache logic (CHANGELOG.md entry 018) must not
defeat a caller that retries the SAME payload on purpose and needs a
genuinely fresh live sample each time - engine/stages/s07_narrate.py's retry
loop depends on this (temperature 0.2 specifically so a validator-rejected
attempt has a real chance at a different result on retry). Without
force_live, this silently broke: every retry after the first replayed
attempt 1's already-rejected cached text instead of calling live again -
found by re-running SC-01 live after the resumability change landed (entry
020)."""

from __future__ import annotations

from dataclasses import dataclass

from engine import config, llm_client


@dataclass(frozen=True)
class _FakeSettings:
    replay_cache: str
    llm_provider: str = "groq"
    llm_model: str = "fake-model"
    llm_endpoint: str = ""
    llm_api_key: str = "fake-key"
    replay_mode: bool = False
    max_llm_calls_per_run: int = 2


def test_force_live_ignores_a_cached_entry_from_an_earlier_attempt(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "load", lambda: _FakeSettings(replay_cache=str(tmp_path)))

    responses = iter(["first response text", "second response text"])
    calls: list[str] = []

    def _fake_call_live(settings, system, user, meta, label="?"):
        text = next(responses)
        calls.append(text)
        return llm_client.LLMResult(text=text, tokens_in=1, tokens_out=1, cost_usd=0.0, from_cache=False)

    monkeypatch.setattr(llm_client, "_call_live", _fake_call_live)

    payload = {"FINDINGS": {"answer": {}}, "PERSONA": "cfo"}

    r1 = llm_client.complete("narrate", payload)
    assert r1.text == "first response text"
    assert len(calls) == 1

    # Without force_live, an identical payload resumes from the cache attempt
    # 1 just wrote - it never reaches _call_live again. This is correct for
    # batch resumability, but exactly what a validator-retry loop must avoid.
    r2 = llm_client.complete("narrate", payload)
    assert r2.text == "first response text"
    assert r2.from_cache is True
    assert len(calls) == 1

    # force_live=True must skip that cache read and get a genuinely fresh
    # sample - what engine/stages/s07_narrate.py's retry loop actually needs.
    r3 = llm_client.complete("narrate", payload, force_live=True)
    assert r3.text == "second response text"
    assert r3.from_cache is False
    assert len(calls) == 2

    # And that fresh result is now what a later resumed run picks up -
    # force_live overwrites the stale cache entry, it doesn't just bypass it.
    r4 = llm_client.complete("narrate", payload)
    assert r4.text == "second response text"
    assert r4.from_cache is True
    assert len(calls) == 2
