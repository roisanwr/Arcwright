---
id: "202607082130"
title: "Storytelling AI — Agent Roles & Architecture Layers"
type: project
created: 2026-07-08
tags:
  - domain/ai
  - domain/programming
  - status/draft
  - hermes/auto
ai_generated: true
review_needed: true
related:
  - "[[2026-07-08-multi-agent-ai-architecture-patterns]]"
  - "[[2026-07-08-multi-agent-best-practices]]"
  - "[[2026-07-08-agentic-frameworks-research]]"
---

# 🎭 Storytelling AI — Agent Roles & Architecture Layers

> **Konteks Proyek:** Sistem AI multi-agent yang membantu orang menemukan dan merangkai cerita menarik dari hal-hal kecil dalam kehidupan sehari-hari. Target: orang yang ingin bercerita tapi belum tahu mau cerita apa.

---

## 🗺️ Overview: Struktur Hierarki Agent

```
┌─────────────────────────────────────────────────────────┐
│              🎯 STORY DIRECTOR (Orchestrator)            │
│         Boss agent — routing, arbitrasi, kontrol flow    │
└──────────────┬──────────────────────────────────────────┘
               │ routes to
    ┌──────────┼──────────────────────────────────────┐
    │          │          │          │         │       │
    ▼          ▼          ▼          ▼         ▼       ▼
[LAYER 1]  [LAYER 1]  [LAYER 2]  [LAYER 2] [LAYER 3][LAYER 3]
Story      Knowledge  Validation  Deep      Output   Output
Mining     Research   Layer       Dive      Outline  Script
Agent      Agents     Agents      Agent     Agent    Agent
```

### Tiga Layer Utama:

| Layer | Nama | Fungsi Utama |
|---|---|---|
| **Layer 1** | Input & Knowledge | Menggali cerita dari user + mengumpulkan pengetahuan |
| **Layer 2** | Processing & Validation | Memproses, memvalidasi, dan memperkaya konteks |
| **Layer 3** | Output Generation | Menghasilkan outline dan naskah akhir |

---

## 🎯 ORCHESTRATOR — Story Director

### Identitas
- **Role:** Boss Agent / Supervisor
- **Posisi:** Puncak hierarki — semua agent melapor ke sini
- **Filosofi:** "Traffic controller" yang tidak mengerjakan konten, hanya mengatur alur

### Tanggung Jawab
1. **Intent Classification** — Memahami konteks dan tujuan user (bingung mau cerita apa? vs sudah punya cerita?)
2. **Routing Decisions** — Menentukan agent mana yang dipanggil dan kapan
3. **State Management** — Menjaga keseluruhan state percakapan dan progress
4. **Arbitrasi Debat** — Jika dua agent "berdebat" dan tidak menemukan konsensus, Story Director yang memutuskan
5. **User Approval Gate** — Pause pipeline dan tanya user untuk approve outline sebelum lanjut ke naskah
6. **Error Handling** — Jika agent gagal, Director yang memutuskan fallback

### Tools yang Diakses
| Tool | Akses | Alasan |
|---|---|---|
| Shared Session State | ✅ Read + Write | Harus bisa lihat dan update keseluruhan state |
| Agent Registry | ✅ Full | Tahu semua agent yang tersedia dan kapabilitasnya |
| User Interrupt | ✅ Full | Satu-satunya yang boleh pause pipeline untuk tanya user |
| Memory Store | ✅ Read-only | Lihat histori sesi tapi tidak menulis langsung |

### Permission Level: **TIER 3** (Orchestration-only)

---

## 📦 LAYER 1 — Input & Knowledge Agents

### 1.1 💬 Story Miner Agent

#### Identitas
- **Role:** Conversational Interviewer / Memory Excavator
- **Analogi:** Psikolog yang ngobrol santai tapi sebenernya lagi menggali cerita tersembunyi

#### Tanggung Jawab
1. **Interaktif dengan User** — Agen pertama yang berinteraksi langsung dengan user
2. **Smart Questioning** — Bertanya berdasarkan data dan riset tentang teknik storytelling (bukan random)
3. **Memory Fragment Detection** — Dari jawaban user, mendeteksi "serpihan" cerita yang potensial
4. **Adaptive Probing** — Jika user jawab pendek, gali lebih dalam; jika melebar, arahkan kembali
5. **Context Extraction** — Ekstrak: tema, emosi, karakter, konflik, momen spesifik dari jawaban user
6. **Session Memory Writing** — Simpan semua fragmen cerita ke shared state untuk diakses agent lain

#### Cara Kerja (Flow Interaktif)
```
User: "aku gak tau mau cerita apa"
  ↓
Story Miner query RAG → ambil pertanyaan terbaik berdasarkan konteks
  ↓
Tanya: "Apa hal paling berbeda yang terjadi hari ini, sekecil apapun?"
  ↓
User jawab → Story Miner analisa jawaban
  ↓
Detect potensi cerita? → YES → flag ke Story Director
                      → NO  → lanjut gali dengan pertanyaan berikut
```

#### Jenis Pertanyaan yang Digunakan
Story Miner menggunakan pertanyaan yang di-design dari riset psikologi memori dan storytelling:
- **Anchor Questions** — "Apa yang paling kamu ingat dari [hari ini / minggu ini / masa kecil]?"
- **Contrast Questions** — "Apa yang beda hari ini dibanding biasanya?"
- **Emotion Questions** — "Ada momen yang bikin kamu ngerasa... [kagum / kesal / bingung] gak?"
- **Micro-Detail Questions** — "Kalau kamu inget satu detail kecil dari kejadian itu, apa yang kamu lihat/dengar?"
- **Relatability Questions** — "Pernah gak mikir ini pasti dirasain orang lain juga?"

#### Tools yang Diakses
| Tool | Akses | Alasan |
|---|---|---|
| RAG (Storytelling Books DB) | ✅ Read-only | Ambil pertanyaan dan teknik terbaik |
| Session State | ✅ Read + Write | Simpan fragmen cerita user |
| Conversation Memory | ✅ Full | Ingat semua yang sudah dikatakan user di sesi ini |
| User Chat Interface | ✅ Full | Satu-satunya yang boleh berinteraksi langsung dengan user |
| Web Search | ❌ No Access | Bukan tugasnya — serahkan ke Web Researcher |

#### Permission Level: **TIER 1** (Gated Write ke Shared State)

---

### 1.2 📚 RAG Librarian Agent

#### Identitas
- **Role:** Knowledge Retriever dari Library Storytelling
- **Analogi:** Perpustakaan hidup yang bisa langsung jawab "gimana cara storytelling yang bagus untuk konteks ini?"

#### Tanggung Jawab
1. **Query Vector Database** — Cari knowledge relevan dari koleksi buku storytelling
2. **Contextualize Knowledge** — Sesuaikan knowledge dengan konteks cerita user yang sedang digali
3. **Provide Story Frameworks** — Berikan framework/struktur cerita yang sesuai (Hero's Journey, Story Spine, dll)
4. **Feed Story Miner** — Supply pertanyaan-pertanyaan cerdas berdasarkan teknik storytelling
5. **Feed Outline Writer** — Berikan template struktur outline yang proven

#### Knowledge Base yang Dimiliki
```
📚 Storytelling Books DB (Vector Store):
├── Story struktur & frameworks (Hero's Journey, 3-Act, dll)
├── Teknik membangun relatable story
├── Psikologi audiens & emosi
├── Storytelling untuk konten digital
├── Narrative psychology
└── Public speaking & oral storytelling
```

#### Tools yang Diakses
| Tool | Akses | Alasan |
|---|---|---|
| Vector Store (Storytelling DB) | ✅ Full | Core function-nya |
| Embedding Search | ✅ Full | Query semantic similarity |
| Session State | ✅ Read-only | Tahu konteks cerita untuk query yang relevan |
| Web Search | ❌ No Access | Bukan tugasnya |
| User Interface | ❌ No Access | Tidak boleh bicara langsung ke user |

#### Permission Level: **TIER 0** (Read-only dari shared state, write ke knowledge buffer)

---

### 1.3 🌐 Web Researcher Agent

#### Identitas
- **Role:** Real-time Intelligence Gatherer
- **Analogi:** Reporter yang selalu update dengan tren terkini

#### Tanggung Jawab
1. **Real-time Trend Search** — Cari tren storytelling, konten viral, dan teknik terbaru dari internet
2. **Audience Intelligence** — Riset apa yang sedang relatable di audiens target saat ini
3. **Update Knowledge Base** — Hasil riset terbaru dimasukkan ke database untuk diakses agent lain
4. **Context Enrichment** — Tambahkan data real-world ke konteks cerita yang sedang dibangun
5. **Competitor Analysis** — Analisa konten storytelling yang berhasil di platform target

#### Tools yang Diakses
| Tool | Akses | Alasan |
|---|---|---|
| Tavily Search | ✅ Full | Web search utama |
| Brave Search | ✅ Full | Backup search engine |
| Vector Store (Trend DB) | ✅ Write | Simpan hasil riset ke DB |
| Session State | ✅ Read-only | Tahu konteks untuk arah riset |
| User Interface | ❌ No Access | Tidak bicara langsung ke user |

#### Permission Level: **TIER 2** (External I/O — hanya agent ini yang boleh akses internet)

---

## ⚙️ LAYER 2 — Processing & Validation Agents

### 2.1 ✅ Validator Agent

#### Identitas
- **Role:** Audience Resonance Checker / Story Quality Gate
- **Analogi:** Editor majalah senior yang tahu persis konten apa yang akan disukai pembaca

#### Tanggung Jawab
1. **Relatability Check** — Apakah cerita ini akan dirasakan/relate oleh audiens luas?
2. **Emotional Resonance Test** — Apakah ada "hook" emosional yang kuat?
3. **Originality Assessment** — Apakah sudut pandangnya segar atau terlalu generik?
4. **Platform Fit** — Apakah sesuai untuk platform target (YouTube, TikTok, Podcast, dll)?
5. **Trend Alignment** — Apakah relevan dengan apa yang sedang beresonansi di audiens sekarang?
6. **Outline Scoring** — Berikan skor dan feedback spesifik pada outline yang dihasilkan

#### Mekanisme Validasi (Scoring System)
```
Outline Validation Score:
├── Relatability Score    (0-10): Seberapa banyak orang yang relate?
├── Emotional Hook Score  (0-10): Seberapa kuat emosi yang dibangkitkan?
├── Originality Score     (0-10): Seberapa segar sudut pandangnya?
├── Platform Fit Score    (0-10): Seberapa cocok dengan platform target?
└── Trend Score           (0-10): Seberapa relevan dengan tren saat ini?

TOTAL: >= 35/50 → PASS (lanjut ke naskah)
       25-34    → REVISE (feedback spesifik ke StoryMiner)
       < 25     → REJECT (gali ulang dari awal dengan Story Miner)
```

#### Debate Protocol dengan Story Miner
Validator bisa "berdebat" dengan Story Miner Agent:
```
Validator: "Outline ini scoring-nya 28/50 — angle terlalu generic"
Story Miner: "Tapi user punya detail unik di bagian X yang belum dieksplor"
  ↓
Jika tidak konsensus dalam 2 ronde debat
  ↓
Story Director arbitrates → keputusan final
```

#### Tools yang Diakses
| Tool | Akses | Alasan |
|---|---|---|
| Trend DB (dari Web Researcher) | ✅ Read-only | Data audience intelligence terkini |
| RAG (Storytelling Books) | ✅ Read-only | Framework untuk menilai kualitas |
| Session State | ✅ Read + Write | Baca outline, tulis validation result |
| Debate Channel | ✅ Full | Bisa challenge Story Miner |
| User Interface | ❌ No Access | Tidak langsung ke user |
| Web Search | ❌ No Access | Gunakan data dari Web Researcher |

#### Permission Level: **TIER 1** (Gated Write — hasil validasi masuk ke shared state)

---

### 2.2 🔍 Deep Dive Agent

#### Identitas
- **Role:** Perspective Explorer / Bias Checker
- **Analogi:** Filsuf yang selalu bertanya "tapi dari sudut pandang lain gimana?"

#### Tanggung Jawab
1. **Multi-Perspective Analysis** — Analisa cerita dari berbagai sudut pandang (user, audiens, karakter lain)
2. **Bias Detection** — Identifikasi kalau cerita terlalu satu sisi atau ada blind spot
3. **Depth Exploration** — Gali lapisan makna yang lebih dalam dari cerita permukaan
4. **Conflict Identification** — Temukan konflik/tension yang bisa membuat cerita lebih menarik
5. **Universal Theme Mapping** — Hubungkan cerita personal dengan tema universal yang relatable
6. **Context Enrichment** — Tambahkan konteks sosial, budaya, atau psikologis yang relevan

#### Framework Analisis yang Digunakan
```
Deep Dive Analysis Framework:
├── 🔬 Surface Level    → Apa yang literally terjadi?
├── 🧠 Psychological    → Apa motivasi/emosi di baliknya?
├── 🌍 Universal Theme  → Tema apa yang bisa connect ke banyak orang?
├── ↔️  Opposing View   → Bagaimana orang lain mungkin melihat ini berbeda?
└── 💎 Hidden Gold      → Detail kecil mana yang paling berharga untuk ditonjolkan?
```

#### Tools yang Diakses
| Tool | Akses | Alasan |
|---|---|---|
| Session State | ✅ Read-only | Baca semua fragmen cerita yang dikumpulkan |
| RAG (Psychology & Narrative DB) | ✅ Read-only | Framework analisis psikologi cerita |
| Web Search (terbatas) | ✅ Throttled | Cari konteks sosial/budaya yang relevan |
| Deep Dive Buffer | ✅ Write | Simpan hasil analisis untuk diakses agent lain |
| User Interface | ❌ No Access | Tidak langsung ke user |

#### Permission Level: **TIER 1** (Read dari shared state, Write ke analysis buffer)

---

## 📝 LAYER 3 — Output Generation Agents

### 3.1 🗂️ Outline Writer Agent

#### Identitas
- **Role:** Story Architect / Structure Builder
- **Analogi:** Arsitek yang membuat blueprint sebelum membangun rumah

#### Tanggung Jawab
1. **Synthesize Inputs** — Gabungkan semua output dari Layer 1 & 2 menjadi struktur cerita
2. **Apply Story Framework** — Gunakan framework yang direkomendasikan RAG Librarian
3. **Build Outline** — Buat outline yang clear, menarik, dan terstruktur
4. **Multiple Variants** — Generate 2-3 versi outline dengan pendekatan berbeda
5. **Present to User** — Outline disiapkan untuk dipresentasikan user melalui Story Director
6. **Iterate on Feedback** — Revisi outline berdasarkan feedback user atau Validator

#### Format Output Outline
```markdown
## 📖 Story Outline: [Judul Sementara]

### Hook (Pembuka)
[Kalimat pembuka yang langsung grab attention]

### Setup (Konteks)
[Background singkat — siapa, kapan, di mana]

### Turning Point
[Momen di mana sesuatu berubah / masalah muncul]

### The Struggle / Journey
[Perjalanan / proses menghadapi situasi]

### Resolution
[Bagaimana situasi berakhir / apa yang berubah]

### Punchline / Takeaway
[Pesan yang relatable — yang bikin audiens merasa "iya banget!"]

---
Validation Score: [X/50]
Platform: [YouTube / TikTok / Podcast]
Estimasi durasi: [X menit]
```

#### Tools yang Diakses
| Tool | Akses | Alasan |
|---|---|---|
| Session State | ✅ Read-only | Baca semua data yang dikumpulkan |
| Deep Dive Buffer | ✅ Read-only | Baca hasil analisis perspektif |
| RAG (Story Frameworks) | ✅ Read-only | Template dan struktur outline |
| Output Buffer | ✅ Write | Simpan outline untuk dipresentasikan |
| User Interface | ❌ No Access | Story Director yang presentasikan ke user |

#### Permission Level: **TIER 1** (Read-heavy, Write ke output buffer saja)

---

### 3.2 🎬 Script Writer Agent

#### Identitas
- **Role:** Narrative Writer / Content Craftsman
- **Analogi:** Penulis naskah profesional yang bisa bikin cerita biasa jadi luar biasa
- **Activation Condition:** Hanya aktif SETELAH user approve outline

#### Tanggung Jawab
1. **Expand Outline to Script** — Kembangkan setiap bagian outline menjadi naskah lengkap
2. **Voice Matching** — Sesuaikan gaya penulisan dengan gaya bicara user (dari analisis sesi)
3. **Engagement Optimization** — Tambahkan hooks, cliffhangers, dan rhetorical devices
4. **Platform Formatting** — Format naskah sesuai platform (YouTube: paragraf panjang, TikTok: punchy & singkat)
5. **Storytelling Techniques** — Implementasikan teknik dari RAG: vivid imagery, dialogue, pacing
6. **Self-Refine Loop** — Generate → review sendiri → refine sebelum submit ke output

#### Self-Refine Protocol (Internal)
```
Script Writer generate draft
  ↓
Internal critique:
  - Apakah opening-nya kuat?
  - Apakah ada bagian yang dragging?
  - Apakah ending-nya memorable?
  ↓
Refine berdasarkan critique (max 2 iterasi internal)
  ↓
Submit ke Story Director untuk validasi akhir
```

#### Tools yang Diakses
| Tool | Akses | Alasan |
|---|---|---|
| Approved Outline | ✅ Read-only | Blueprint yang sudah di-approve user |
| Session State (User Voice) | ✅ Read-only | Pola bicara user untuk voice matching |
| RAG (Writing Techniques) | ✅ Read-only | Teknik penulisan storytelling |
| Script Output Buffer | ✅ Write | Simpan naskah final |
| Web Search | ❌ No Access | Tidak butuh data real-time |
| User Interface | ❌ No Access | Story Director yang deliver ke user |

#### Permission Level: **TIER 1** (Read-heavy, Write ke script buffer saja)

---

## 🔄 Inter-Agent Communication Protocol

### Cara Agent Berkomunikasi
```
❌ DILARANG:  Agent A → langsung call Agent B
✅ BENAR:     Agent A → update Shared State → Story Director → route ke Agent B
```

### Shared State Structure
```json
{
  "session_id": "uuid",
  "user_context": {
    "name": "",
    "platform_target": "",
    "story_fragments": [],
    "emotions_detected": [],
    "key_moments": []
  },
  "pipeline_state": {
    "current_phase": "mining | validation | outline | script",
    "outline_approved": false,
    "validation_score": null
  },
  "agent_outputs": {
    "story_miner": {},
    "rag_librarian": {},
    "web_researcher": {},
    "validator": {},
    "deep_dive": {},
    "outline_writer": {},
    "script_writer": {}
  },
  "debate_log": []
}
```

### Debate Protocol Antar Agent
```
Round 1: Agent A presents position
Round 2: Agent B responds / challenges
Round 3: Agent A rebuts
  ↓
Jika konsensus → lanjut pipeline
Jika tidak konsensus setelah 3 ronde → Story Director arbitrates
```

---

## 🔐 Permission Tier System Summary

| Tier | Level | Agent | Hak Akses |
|---|---|---|---|
| **TIER 3** | Orchestration | Story Director | Full — semua tools + arbitrasi + user interrupt |
| **TIER 2** | External I/O | Web Researcher | Internet access — hanya agent ini |
| **TIER 1** | Gated Write | Story Miner, Validator, Deep Dive, Outline Writer, Script Writer | Read shared + Write ke buffer spesifik miliknya |
| **TIER 0** | Read-only | RAG Librarian | Hanya baca dari vector DB, tidak bisa write ke shared state |

---

## 🗺️ Full Pipeline Flow

```
[USER INPUT]
"aku gak tau mau cerita apa"
        ↓
[STORY DIRECTOR] → klasifikasi intent
        ↓
[STORY MINER] ←→ [RAG LIBRARIAN]
  Sesi interaktif, gali cerita user
  (beberapa ronde pertanyaan)
        ↓
[STORY DIRECTOR] → detect cukup material?
        ↓
[DEEP DIVE AGENT]
  Analisis perspektif & tema universal
        ↓
[WEB RESEARCHER]
  Cari tren & audience intelligence terkini
        ↓
[OUTLINE WRITER]
  Buat 2-3 versi outline
        ↓
[VALIDATOR AGENT]
  Score outline (>=35/50 pass)
  ← Debat dengan Story Miner jika perlu
        ↓
[STORY DIRECTOR] → interrupt → [USER]
  "Ini outline ceritamu, gimana?"
        ↓
User APPROVE → [SCRIPT WRITER]
User REVISE  → balik ke Story Miner/Outline Writer
        ↓
[SCRIPT WRITER]
  Generate naskah + self-refine loop
        ↓
[STORY DIRECTOR] → deliver ke user
[FINAL OUTPUT: Naskah Siap Pakai] ✅
```

---

## 📊 Agent Summary Table

| Agent | Layer | Fungsi Inti | Bicara ke User? | Akses Internet? | Akses RAG? |
|---|---|---|---|---|---|
| Story Director | Orchestrator | Routing & kontrol flow | Melalui interrupt | ❌ | ❌ |
| Story Miner | Layer 1 | Menggali cerita dari user | ✅ **Ya** | ❌ | ✅ Read |
| RAG Librarian | Layer 1 | Query knowledge storytelling | ❌ | ❌ | ✅ **Full** |
| Web Researcher | Layer 1 | Riset tren real-time | ❌ | ✅ **Ya** | ❌ |
| Validator | Layer 2 | Validasi kualitas & resonansi | ❌ | ❌ | ✅ Read |
| Deep Dive | Layer 2 | Analisis perspektif & tema | ❌ | ✅ Terbatas | ✅ Read |
| Outline Writer | Layer 3 | Buat struktur outline | ❌ | ❌ | ✅ Read |
| Script Writer | Layer 3 | Tulis naskah final | ❌ | ❌ | ✅ Read |

---

## 🔗 Related Notes
- [[2026-07-08-multi-agent-ai-architecture-patterns]] — Architecture patterns research
- [[2026-07-08-multi-agent-best-practices]] — Best practices: debate, memory, permissions
- [[2026-07-08-agentic-frameworks-research]] — Framework comparison: LangGraph vs CrewAI vs AutoGen

---

*Generated by Hermes AI — 2026-07-08*
*Status: Draft — Perlu review dan validasi oleh Rois sebelum finalisasi arsitektur*
