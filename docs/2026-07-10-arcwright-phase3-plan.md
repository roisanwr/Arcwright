---
id: "202607102200"
title: "Arcwright Fase 3 — Production Polish & Quality Assurance"
type: project
created: 2026-07-10
tags:
  - domain/ai
  - domain/programming
  - status/draft
  - hermes/auto
ai_generated: true
review_needed: true
related:
  - "[[2026-07-10-arcwright-pla]]"
  - "[[2026-07-10-arcwright-technical-architecture]]"
---

# 🏁 Arcwright Fase 3 — Production Polish & Quality Assurance

> **Based on:** Hermes Stack research + codebase audit of current Fase 2 state
> **Status:** Error handling sudah ada (try/except di semua agent), logging sudah ada (logging module). Yang kurang: retry, graceful degradation, observability, output formatting, documentation, tests.

---

## 📊 Hasil Audit Codebase (Fase 2)

| Aspek | Status | Detail |
|-------|:------:|--------|
| **Error handling (try/except)** | ✅ Ada | Semua agent punya try/except, tapi bare minimum — langsung return empty dict |
| **Retry logic** | ❌ Belum | Kalau agent gagal, langsung return error — gak ada percobaan ulang |
| **Graceful degradation** | ❌ Belum | Satu agent gagal → state kosong → agent downstream gagal juga |
| **Logging** | ✅ Ada | Pake Python `logging` module, tapi belum ada format standar |
| **LangSmith tracing** | ❌ Belum | LangGraph udah auto-compatible, tinggal set env var |
| **Output formatting** | ❌ Belum | Script masih return raw dict — belum diformat rapi buat user |
| **CLI (`main.py`)** | ⚠️ Dasar | Udah bisa interaktif tapi error handling CLI minimal |
| **Test suite** | ❌ Belum | Nol test — cuma ad-hoc verification pas build |
| **Documentation** | ❌ Belum | README masih ngomongin RAG doang, belom update agents |
| **Cost tracking** | ❌ Belum | Gak tau berapa token tiap agent pake |

---

## 🗺️ Roadmap Fase 3

### ⚡ Prioritas Tinggi (Hari 1-3)

#### 3.1 Retry Logic & Graceful Degradation
**Goal:** Kalau agent gagal, pipeline tetap jalan

```python
# Pattern yang akan diimplementasikan di setiap agent
def safe_agent_call(agent_fn, state, max_retries=2):
    """Wrapper: retry 2x, kalau gagal return partial state."""
    for attempt in range(max_retries):
        try:
            return agent_fn(state)
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"[{agent_fn.__name__}] Attempt {attempt+1} failed: {e}")
            continue
        except Exception as e:
            logger.error(f"[{agent_fn.__name__}] Fatal: {e}")
            break
    
    # Graceful degradation — return partial state instead of crashing
    return {
        "error_count": state.get("error_count", 0) + 1,
        "agent_notes": [{
            "agent": agent_fn.__name__,
            "note_type": "flag",
            "content": f"Agent failed after {max_retries} attempts"
        }]
    }
```

**Task breakdown:**
- [ ] 3.1a Buat `safe_agent_call()` decorator/wrapper di `graph/pipeline.py`
- [ ] 3.1b Apply ke semua 8 agent nodes
- [ ] 3.1c Test: matiin ChromaDB → RAG Librarian gagal → pipeline lanjut tanpa RAG
- [ ] 3.1d Test: matiin internet → Web Researcher gagal → pipeline lanjut
- [ ] 3.1e Test: kasih state kosong → agent return partial → director skip ke phase next

**Deliverable:** Pipeline bisa handle semua failure mode tanpa crash

---

#### 3.2 Output Formatting — Platform Variants
**Goal:** Script output rapi, bisa milih platform

```python
# Format yang akan dihasilkan script_writer_node:

# YouTube (3-10 menit)
YOUTUBE_FORMAT = """
# [JUDUL]
# ⏱️ Durasi: 3-5 menit

[HOOK — 15 detik pertama]
…

[BODY — Cerita utama]
…

[OUTRO — Call to action]
…
"""

# TikTok (60-90 detik)
TIKTOK_FORMAT = """
[HOOK — 3 detik pertama, langsung menarik]
…

[BODY — Padat, emosional, pace cepat]
…

[CLOSING — Satu kalimat memorable]
…
"""

# Podcast (5-15 menit)
PODCAST_FORMAT = """
# [JUDUL EPISODE]
# Durasi: ~10 menit

[PEMBUKAAN — Host intro]
…

[CERITA — Natural, conversational]
…

[PENUTUP — Kesimpulan + teaser next]
…
"""

# Blog
BLOG_FORMAT = """
---
title: "..."
date: ...
tags: [...]
---

## [Hook — Paragraf pembuka]
…

## [Body — Cerita lengkap]
…

## [Takeaway — Relatable insight]
…
"""
```

**Task breakdown:**
- [ ] 3.2a Update `script_writer.py` — tambah platform-specific formatting
- [ ] 3.2b Update `outline_writer.py` — tambah platform detection dari user input
- [ ] 3.2c Update `main.py` — kasih opsi platform pas mulai sesi
- [ ] 3.2d Save output ke file `.md` otomatis di `output/scripts/`
- [ ] 3.2e Copy output path ke clipboard atau print path

**Deliverable:** Script output rapi dengan 4 format platform + auto-save file

---

#### 3.3 LangSmith Observability
**Goal:** Bisa trace & debug pipeline

**Setup (cuma 3 baris):**
```bash
export LANGCHAIN_TRACING_V2=true
export LANGCHAIN_API_KEY=lsv2_...
export LANGCHAIN_PROJECT=arcwright
```

**Task breakdown:**
- [ ] 3.3a Tambah env vars ke `config/settings.py`
- [ ] 3.3b Set `LANGCHAIN_CALLBACKS` di `main.py`
- [ ] 3.3c Test: jalankan 1 sesi → cek LangSmith dashboard
- [ ] 3.3d Dokumentasi cara setup di README

**Deliverable:** Setiap sesi tercatat di LangSmith dengan full traces

---

### 📋 Prioritas Sedang (Hari 4-5)

#### 3.4 Test Suite
**Goal:** Pipeline bisa di-test tanpa actual API calls (pake mock)

```
tests/
├── __init__.py
├── conftest.py              ← Mock LLM, fixtures
├── test_rag_librarian.py    ← Test query building, empty DB
├── test_story_miner.py      ← Test question generation, fragment extraction
├── test_deep_dive.py        ← Test 5-perspective analysis
├── test_web_researcher.py   ← Test query building, search failure
├── test_validator.py        ← Test scoring >35, <35, debate logic
├── test_outline_writer.py   ← Test outline generation
├── test_script_writer.py    ← Test self-refine loop
├── test_story_director.py   ← Test all 12+ routing branches
├── test_pipeline_integration.py  ← Test full flow (mocked)
```

**Task breakdown:**
- [ ] 3.4a Buat `conftest.py` dengan mock LLM + fixtures
- [ ] 3.4b Test routing: coverage semua 12+ conditional branches
- [ ] 3.4c Test validator: skor 20 (reject), 30 (revise), 40 (pass)
- [ ] 3.4d Test debate loop: max 3 rounds
- [ ] 3.4e Test graceful degradation: matikan RAG → pipeline tetap jalan
- [ ] 3.4f Integration test: mock full user session → output script

**Deliverable:** 20+ test cases, runnable via `pytest tests/`

---

#### 3.5 Inter-Agent Logging & Monitoring
**Goal:** Tiap langkah pipeline tercatat untuk debugging

```python
# Akan ditambahkan di graph/pipeline.py sebagai node wrapper
def logged_agent(agent_name: str, agent_fn):
    """Wrap agent node with logging."""
    def wrapped(state):
        logger.info(f"[{agent_name}] Starting. Phase: {state.get('current_phase')}")
        start = time.time()
        result = agent_fn(state)
        elapsed = time.time() - start
        logger.info(f"[{agent_name}] Done in {elapsed:.2f}s")
        return result
    return wrapped
```

**Task breakdown:**
- [ ] 3.5a Buat `logged_agent` wrapper
- [ ] 3.5b Tambah timing per agent
- [ ] 3.5c Log ke file `logs/arcwright-{date}.log`
- [ ] 3.5d Tambah structured JSON logging (opsional)

**Deliverable:** Setiap agent call tercatat dengan timing + result status

---

### 🎯 Prioritas Ringan (Hari 6-7)

#### 3.6 Documentation Update
**Goal:** README + docs mencerminkan state project sekarang

- [ ] 3.6a Update `README.md` — progress bar, cara jalanin, semua fitur
- [ ] 3.6b Update `AGENTS.md` — struktur project terkini
- [ ] 3.6c Buat `docs/2026-07-10-arcwright-phase3-complete.md` — laporan akhir
- [ ] 3.6d Update docs di vault Obsidian (Inbox)

---

#### 3.7 CLI Polish
- [ ] 3.7a Better error messages (kalo API key gak ada, kasih tau cara set)
- [ ] 3.7b Progress indicator (spinner atau status text)
- [ ] 3.7c Save session history ke file
- [ ] 3.7d Color output (pake `rich` atau ANSI codes)

---

#### 3.8 Cost Tracking (Opsional)
- [ ] 3.8a Track token usage per agent call
- [ ] 3.8b Simulasi cost berdasarkan model pricing
- [ ] 3.8c Report per sesi: "Sesi ini pake 4.2K tokens = ~$0.02"

---

## 📅 Timeline

| Day | Tasks | Total Est. |
|:---:|-------|:----------:|
| **1** | 3.1 Retry + graceful degradation | 4-6 jam |
| **2** | 3.2 Output formatting (4 platform) | 4-6 jam |
| **3** | 3.3 LangSmith tracing + 3.5 Inter-agent logging | 3-4 jam |
| **4** | 3.4 Test suite (unit + integration) | 5-7 jam |
| **5** | Test suite lanjutan + bug fixes | 4-5 jam |
| **6** | 3.6 Documentation + 3.7 CLI polish | 3-5 jam |
| **7** | Cadangan / review / git push | 2-3 jam |

**Total estimasi:** ~25-35 jam (3-4 hari full)

---

## 🚨 Risk Register Fase 3

| Risk | Likelihood | Impact | Mitigasi |
|------|:----------:|:------:|----------|
| **Mock LLM berbeda behavior dari real LLM** | MEDIUM | MEDIUM | Test dengan real LLM di akhir siklus |
| **LangSmith API key setup** | LOW | LOW | Gratis tier cukup untuk dev |
| **Output formatting kok gak sesuai platform** | MEDIUM | LOW | Prompt engineering di script_writer |
| **Retry bikin pipeline makin lambat** | LOW | MEDIUM | Max 2 retry, timeout 15s |

---

## ✅ Success Criteria Fase 3

| Criterion | Target | Cara Ukur |
|-----------|:------:|-----------|
| Pipeline gak crash saat agent gagal | 100% | Simulasi failure tiap agent |
| Output script rapi per platform | ≥4 platform | Manual review |
| LangSmith traces muncul | ✓ | Cek dashboard |
| Test coverage routing | ≥90% | `pytest --cov` |
| Test coverage validator logic | 100% | Branch coverage |
| README updated | ✓ | Visual check |
| Total waktu | ≤7 hari | Calendar |

---

*Generated by Yui on 2026-07-10 — Based on Hermes Stack research + codebase audit*
