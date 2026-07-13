# Forge v2 — Multi-Strategy Chunking Engine

> **Status:** Planning Phase  
> **Target:** Enterprise-grade document chunking pipeline yang reusable untuk project mana pun  
> **Resources:** Ryzen 9 7900X (CPU) · GPU 16GB VRAM (CUDA) · Free Reasoning API (LLM)  

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Vision & Goals](#2-vision--goals)
3. [Full Pipeline Architecture](#3-full-pipeline-architecture)
4. [Layer Details](#4-layer-details)
   - [Layer 1: Extraction](#41-layer-1-extraction)
   - [Layer 2: Markdown Cleanup (LLM)](#42-layer-2-markdown-cleanup-llm)
   - [Layer 3: Strategy Analyzer (LLM)](#43-layer-3-strategy-analyzer-llm)
   - [Layer 4: Structural Chunking (CPU)](#44-layer-4-structural-chunking-cpu)
   - [Layer 5: Semantic Refiner (GPU)](#45-layer-5-semantic-refiner-gpu)
   - [Layer 6: Contextual Enhancer (LLM)](#46-layer-6-contextual-enhancer-llm)
   - [Layer 7: Embedding & Storage (GPU)](#47-layer-7-embedding--storage-gpu)
5. [Strategy Detection Logic](#5-strategy-detection-logic)
6. [Hardware Utilization Map](#6-hardware-utilization-map)
7. [Module Structure](#7-module-structure)
8. [Implementation Roadmap](#8-implementation-roadmap)
9. [Reusability Design](#9-reusability-design)
10. [Appendices](#10-appendices)

---

## 1. Current State Analysis

### Kondisi Sekarang

| Aspek | Detail |
|---|---|
| Jumlah buku | 10 dari target 29 |
| Total chunks | 518 |
| Rata-rata chunk size | 1,586 chars |
| Strategi chunking | Heading-based (H1/H2/H3 only) |
| Pre-processing | None |
| Post-processing | None |
| GPU utilization | None |
| LLM utilization | None |
| Chunk quality (baik) | 2/10 buku (20%) |

### Masalah Teridentifikasi

1. **Empty heading markers** — 69 baris `### ` tanpa teks di On Writing, regex chunker tidak mendeteksi sebagai boundary
2. **H4 diabaikan** — The Hero with 1000 Faces punya 287 H4 + 82 H1-H3 = 82 boundary potensial, tapi H4 di-skip
3. **XML artifacts** — `<?xml version='1.0' encoding='utf-8'?>` mencemari embedding
4. **Chunk oversized** — Story Genius cuma 2 chunk untuk 511K chars karena H1 terlalu jarang
5. **No context** — Chunk disimpan tanpa deskripsi posisi dalam dokumen
6. **Fixed strategy** — Semua buku pake cara yang sama, padahal struktur berbeda

---

## 2. Vision & Goals

### Target

| Metrik | Sekarang | Target Forge v2 |
|---|---|---|
| Total chunks (29 buku) | ~1,500 | **8,000–12,000** |
| Chunk size range | 100–3,982 chars | **150–2,500 chars** (optimal) |
| Chunk quality (baik) | 20% buku | **95%+ buku** |
| Strategy selection | Fixed (heading only) | **Adaptive per buku** |
| Pre-processing | None | LLM-assisted cleanup |
| GPU used | ❌ | ✅ BGE-M3 via CUDA |
| LLM used | ❌ | ✅ Analyzer + Enhancer |
| Reusable package | ❌ (tied to forge/) | ✅ `pip install` anywhere |

### Prinsip Desain

1. **Adaptif** — Setiap buku dianalisis individually, strategi dipilih otomatis
2. **Modular** — Setiap layer bisa dipake sendiri-sendiri
3. **Reusable** — Bisa `pip install` dan pake di project lain
4. **Resource-optimized** — GPU untuk embedding, CPU untuk string ops, LLM untuk analisis
5. **Deterministic** — Hasil yang sama untuk input yang sama (cacheable)

---

## 3. Full Pipeline Architecture

```
📁 FILE MENTAH (PDF/EPUB/MOBI/DOCX/TXT/HTML)
   │
   ▼
┌──────────────────────────────────────────────────┐
│ 🗃️  LAYER 1: EXTRACTION                         │
│    ├── PDF     → marker-pdf (OCR: CPU + GPU)     │
│    ├── EPUB    → ebooklib + BeautifulSoup        │
│    ├── MOBI    → mobi + markdownify              │
│    ├── DOCX    → python-docx                     │
│    ├── TXT     → langsung baca                   │
│    └── HTML    → BeautifulSoup + markdownify      │
│                                                   │
│    Output: Raw Markdown                           │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 🧹 LAYER 2: MARKDOWN CLEANUP (LLM)               │
│    ├── Hapus XML artifacts (<?xml...?>)           │
│    ├── Hapus empty headings (### spasi doang)     │
│    ├── Hapus image references (![](...))          │
│    ├── Gabung kata terpisah OCR ("T H E" → "THE") │
│    ├── Hapus header/footer artifacts              │
│    └── [LLM] Deteksi FOREWORD vs MAIN CONTENT     │
│                                                   │
│    Hardware: Free Reasoning API                   │
│    ⏱ ~10–20 detik per buku                       │
│    Output: Clean Markdown                         │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 🧠 LAYER 3: STRATEGY ANALYZER (LLM)              │
│    ├── Hitung heading density                     │
│    ├── Analisis tipe konten (narasi/teknis/dll)   │
│    ├── [LLM] Rekomendasi strategi chunking        │
│    ├── [LLM] Chunk size optimal                   │
│    ├── [LLM] H4 as boundary? (yes/no)             │
│    └── [LLM] Special instructions (appendix, tabel)│
│                                                   │
│    Cache: Hasil disimpan, tidak diulang           │
│    Hardware: Free Reasoning API                   │
│    ⏱ ~3–5 detik per buku                         │
│    Output: Strategy config dict                   │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ ✂️  LAYER 4: STRUCTURAL CHUNKING (CPU)            │
│    ├── Split berdasarkan heading sesuai strategi  │
│    │   (H1/H2/H3, opsional H4)                   │
│    ├── Metadata per chunk:                        │
│    │   • id (hash dari content)                   │
│    │   • title (heading terdekat)                 │
│    │   • section (H1/H2 context)                  │
│    │   • source (nama file)                       │
│    │   • char_count                               │
│    └── Config dari Layer 3 (adaptive)             │
│                                                   │
│    Hardware: Ryzen 9 7900X (CPU)                  │
│    ⏱ ~0.1 detik per buku                         │
│    Output: List of raw chunks                     │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 🎯 LAYER 5: SEMANTIC REFINER (GPU)               │
│    ├── Deteksi chunk oversized (>3000 chars)      │
│    │   → Split berdasarkan topic shift            │
│    │   • Bagi chunk jadi sentences                │
│    │   • Sliding window 5 kalimat                 │
│    │   • Embed tiap window via BGE-M3 (CUDA)     │
│    │   • Cosine similarity → deteksi boundary     │
│    │   • Split di titik similarity < 0.7          │
│    │                                              │
│    ├── Deteksi chunk tiny (<150 chars)            │
│    │   → Merge dengan chunk terdekat              │
│    │                                              │
│    └── Deteksi similarity adjacent chunks         │
│        → Merge jika cosine sim > 0.95             │
│        (konten hampir identik secara semantik)     │
│                                                   │
│    Hardware: GPU 16GB VRAM (CUDA)                 │
│    ⏱ ~10–30 detik per buku besar                 │
│    Output: Refined chunks                         │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 🌟 LAYER 6: CONTEXTUAL ENHANCER (LLM)             │
│    ├── Generate ringkasan global buku (1x)        │
│    ├── Tiap chunk dikasih konteks:                │
│    │   "[BAB 3: THE GRIEF] Adegan setelah istri   │
│    │    John meninggal, protag masih denial..."    │
│    ├── Konteks ditempel di depan chunk             │
│    ├── Yang di-embed = konteks + chunk asli       │
│    │                                              │
│    ├── Batch 10 chunk per LLM call                │
│    └── Hanya jalan SEKALI pas indexing            │
│                                                   │
│    Hardware: Free Reasoning API                   │
│    ⏱ ~20–40 detik per buku                       │
│    Output: Context-enriched chunks                │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────┐
│ 🧠 LAYER 7: EMBEDDING & STORAGE (GPU)            │
│    ├── BGE-M3 via CUDA (1024-d vectors)           │
│    ├── Batch processing (batch_size=64)           │
│    ├── Simpan di ChromaDB / Qdrant                │
│    └── Metadata: source, title, section, konteks  │
│                                                   │
│    Hardware: GPU 16GB VRAM (CUDA)                 │
│    ⏱ ~30 detik – 2 menit per buku                │
│    Output: Vector DB collection                   │
└───────────────────┬──────────────────────────────┘
                    │
                    ▼
             💾 CHROMADB / QDRANT
        (siap di-query oleh agents/)
```

---

## 4. Layer Details

### 4.1 Layer 1: Extraction

**Existing code** — sudah berfungsi di `forge/arcwright/extract.py`.  
**Catatan:** Layer ini tidak diubah di Forge v2, hanya potensi enhancement:

```python
# Enhancement opsional — GPU acceleration untuk marker-pdf
# marker-pdf support CUDA untuk OCR processing
config = {
    "force_ocr": True,
    "use_llm": False,  # Bisa di-enable kalo butuh OCR lebih akurat
}
```

### 4.2 Layer 2: Markdown Cleanup (LLM)

**File target:** `forge/arcwright/cleanup.py` (baru)

```python
"""
Markdown cleanup layer.
Menggunakan LLM (Free Reasoning API) untuk membersihkan
extracted markdown dari artifact OCR dan formatting errors.
"""

CLEANUP_PROMPT = """Kamu adalah document cleaner spesialis.
Bersihkan markdown berikut dari artifact dan formatting error.

ATURAN:
1. Hapus semua XML declarations: <?xml version='1.0'...?>
2. Hapus empty heading lines: "### " atau "## " tanpa teks
3. Hapus image references: ![alt](path)
4. Hapus page number artifacts: "|| 45 ||" atau "[page 45]"
5. Gabung kata terpisah oleh spasi aneh: "T H E" → "THE", "C H A P T E R" → "CHAPTER"
6. Hapus horizontal rules: "---" beruntun (>2 berturut-turut)
7. Rapihin tabel yang pake format OCR kacau
8. JANGAN ubah konten narasi/kalimat asli
9. JANGAN potong atau ringkas teks

INPUT:
{extracted_text}

OUTPUT: (hanya markdown bersih, tanpa penjelasan)
"""
```

**Alur:**
1. Terima raw markdown dari Layer 1
2. Regex-based pre-clean (cepat):
   - `re.sub(r'<\?xml[^>]*\?>', '', text)` — hapus XML
   - `re.sub(r'^#{1,4}\s*$', '', text, flags=re.MULTILINE)` — hapus empty headings
   - `re.sub(r'!\[.*?\]\(.*?\)', '', text)` — hapus image refs
3. LLM-based deep-clean (jika diperlukan):
   - Kirim 2000 chars pertama + 2000 chars terakhir
   - LLM deteksi pattern aneh & kasi rekomendasi fix
4. Terapkan fix yang direkomendasikan
5. Output: Clean markdown

### 4.3 Layer 3: Strategy Analyzer (LLM)

**File target:** `forge/arcwright/strategy.py` (baru)

```python
"""
Strategy analyzer — menentukan strategi chunking optimal
untuk setiap buku berdasarkan analisis struktur + LLM.
"""

ANALYZER_PROMPT = """Kamu adalah expert document structure analyst.
Analisis buku ini dan tentukan strategi chunking terbaik.

DATA STRUKTUR:
- Total karakter: {total_chars}
- Total baris: {total_lines}
- Jumlah heading H1: {h1_count}
- Jumlah heading H2: {h2_count}
- Jumlah heading H3: {h3_count}
- Jumlah heading H4: {h4_count}
- Empty heading markers: {empty_headings}
- XML artifacts: {xml_count}
- Heading density: {heading_density:.4f} (headings per line)

PREVIEW KONTEN (500 chars pertama):
{content_preview}

HEADING STRUCTURE (first 50):
{heading_structure}

Tugas:
1. Tentukan tipe buku: "narasi" | "teknis" | "mixed" | "referensi"
2. Rekomendasi strategi chunking: "heading_based" | "hybrid" | "semantic" | "recursive"
3. Apakah H4 perlu dijadikan chunk boundary? (true/false)
4. Chunk size optimal (min chars, max chars)
5. Estimasi jumlah chunk
6. Catatan khusus (apendix, tabel, foreword, dll)

Output JSON SAJA (no markdown):
{{
    "book_type": "narasi",
    "strategy": "hybrid",
    "use_h4_as_boundary": false,
    "chunk_size_min": 150,
    "chunk_size_max": 2500,
    "estimated_chunks": 45,
    "special_notes": [
        "Foreword by Stephen King — pisahkan dari main content",
        "Appendix A punya tabel kronologis — butuh special handling"
    ]
}}
"""
```

**Fallback (jika LLM tidak available):**
```python
def analyze_offline(text: str) -> dict:
    """Heuristic-based analysis tanpa LLM."""
    lines = text.split('\n')
    h1 = len(re.findall(r'^# ', text, re.MULTILINE))
    h2 = len(re.findall(r'^## ', text, re.MULTILINE))
    h3 = len(re.findall(r'^### ', text, re.MULTILINE))
    h4 = len(re.findall(r'^#### ', text, re.MULTILINE))
    empty = len(re.findall(r'^#{1,4}\s*$', text, re.MULTILINE))
    xml_count = text.count('<?xml')
    
    total_headings = h1 + h2 + h3 + h4
    heading_density = total_headings / max(len(lines), 1)
    
    # Decision tree
    if heading_density > 0.05:
        strategy = "heading_based"
        use_h4 = (h4 > total_headings * 0.3)
    elif total_headings > 0:
        strategy = "hybrid"
        use_h4 = (h4 > total_headings * 0.3)
    else:
        strategy = "recursive"
        use_h4 = False
    
    return {
        "strategy": strategy,
        "use_h4_as_boundary": use_h4,
        "chunk_size_min": 150,
        "chunk_size_max": 2500,
        "estimated_chunks": max(total_headings, 10),
    }
```

### 4.4 Layer 4: Structural Chunking (CPU)

**File target:** `forge/arcwright/chunk.py` (refactor dari existing)

```python
"""
Structural chunking — split markdown by heading structure.
Mendukung H1/H2/H3 (opsional H4) sesuai konfigurasi dari Layer 3.
"""

def chunk_by_headings(
    text: str,
    source_name: str,
    use_h4: bool = False,
    min_chars: int = 150,
    max_chars: int = 2500,
) -> list:
    """
    Split markdown jadi chunks berdasarkan heading boundaries.
    
    Args:
        text: Clean markdown dari Layer 2
        source_name: Nama file/sumber
        use_h4: Whether to treat H4 as chunk boundary
        min_chars: Minimum chars per chunk (below = merge)
        max_chars: Maximum chars per chunk (above = flagged for Layer 5)
    
    Returns:
        List of chunk dicts with metadata
    """
    # ... (heading regex, save_chunk logic, filtering)
```

**Key changes from existing:**
- Configurable heading levels (H4 toggle)
- Configurable min/max chars (dari Layer 3)
- Tidak ada hardcoded `CHUNK_MIN_CHARS=100` — ambil dari config
- Flag chunk oversized untuk Layer 5, bukan langsung discard/filter
- Metadata includes `flagged_for_refine: bool`

### 4.5 Layer 5: Semantic Refiner (GPU)

**File target:** `forge/arcwright/refiner.py` (baru)

```python
"""
Semantic refiner — menggunakan BGE-M3 via CUDA untuk:
1. Split chunk oversized berdasarkan topic shift
2. Merge chunk yang secara semantik hampir identik
3. Validasi kualitas chunk secara semantik
"""

import torch
import numpy as np
from sentence_transformers import SentenceTransformer


class SemanticRefiner:
    """
    GPU-accelerated semantic chunk refinement.
    
    Memanfaatkan BGE-M3 embedding model yang sama dengan
    layer embedding, jalan di CUDA.
    """
    
    def __init__(self, device: str = "cuda"):
        self.model = SentenceTransformer(
            'BAAI/bge-m3',
            device=device if torch.cuda.is_available() else 'cpu'
        )
        self.batch_size = 64
        print(f"  🔥 Semantic Refiner: {self.model.device}")
    
    def split_oversized(self, chunks: list, max_chars: int = 2500,
                        threshold: float = 0.7) -> list:
        """
        Split chunk yang melebihi max_chars berdasarkan topic shift.
        
        Algoritma:
        1. Split chunk jadi sentences (by .!?)
        2. Sliding window 5 sentences, stride 1
        3. Embed tiap window → BGE-M3 via CUDA
        4. Cosine similarity antar window berurutan
        5. Jika similarity < threshold → topic shift → split point
        6. Split chunk di titik tersebut
        """
        pass
    
    def merge_similar_adjacent(self, chunks: list,
                                threshold: float = 0.95) -> list:
        """
        Merge 2 chunk berurutan jika secara semantik hampir identik.
        
        Berguna untuk:
        - Chunk pendek yang dipisah by heading tapi konten nyambung
        - Paragraf terakhir bab A dengan paragraf pertama bab B
          yang sebenarnya masih satu kesatuan
        """
        pass
    
    def compute_coherence(self, chunk: str) -> float:
        """
        Hitung coherence score chunk.
        
        Cara: split chunk jadi sentences, embed, hitung
        rata-rata similarity antar semua pasangan.
        Score mendekati 1 = sangat koheren (topik tunggal)
        Score < 0.5 = kemungkinan campur aduk topik
        """
        pass
```

### 4.6 Layer 6: Contextual Enhancer (LLM)

**File target:** `forge/arcwright/enhancer.py` (baru)

```python
"""
Contextual enhancer — memberikan konteks posisi untuk setiap chunk
menggunakan LLM (Free Reasoning API).

Ini mengadaptasi teknik "Contextual Retrieval" dari Anthropic:
https://www.anthropic.com/news/contextual-retrieval
"""

ENHANCE_PROMPT = """Kamu adalah context enhancer untuk RAG system.

Seluruh dokumen (ringkasan):
{full_summary}

Chunk yang perlu dikontekstualisasi:
{chunk_text}

Tugas:
Generate 1 kalimat konteks yang menjelaskan:
1. Posisi chunk ini dalam dokumen (bab/section mana)
2. Topik utama chunk ini
3. Hubungan dengan konteks sebelum/sesudah (jika relevan)

FORMAT KELUARAN:
"[BAB X: JUDUL BAB] — Kalimat konteks singkat..."

CONTOH:
Input chunk: "Dia menutup pintu pelan-pelan. Air matanya jatuh."
Output konteks: "[BAB 3: THE GRIEF] — Adehan setelah istri John meninggal,
protagonist masih dalam fase denial, menolak menerima kenyataan."

OUTPUT: (hanya teks konteks, satu kalimat, tanpa markdown)
"""
```

**Batch strategy:**
```python
def enhance_chunks(chunks: list, full_text: str, api_fn) -> list:
    """
    Enhance chunks with context in batches.
    
    Strategy:
    1. Generate global summary (1 LLM call)
    2. Process chunks in batches of 10 (parallel)
    3. Prepend context to each chunk
    4. Return enriched chunks
    
    Total LLM calls per buku: 1 (summary) + ceil(N/10)
    Untuk 100 chunks = ~11 calls ≈ 20-40 detik
    """
```

### 4.7 Layer 7: Embedding & Storage (GPU)

**File target:** `forge/arcwright/embed.py` (refactor dari existing)

```python
"""
Embedding & vector storage.
Enhanced: GPU acceleration + batch processing + metadata enriched.
"""

def embed_and_store(
    chunks: list,
    collection_name: str,
    device: str = "cuda",
    batch_size: int = 64,
) -> dict:
    """
    Embed enriched chunks and store in vector DB.
    
    Yang di-embed: context + chunk_text (bukan chunk_text aja)
    Metadata: source, title, section, konteks, char_count
    
    GPU: BGE-M3 via CUDA, batch_size=64 untuk throughput maksimal
    """
    model = SentenceTransformer('BAAI/bge-m3', device=device)
    client = chromadb.PersistentClient(path=config.CHROMA_DIR)
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [c["text_for_embedding"] for c in batch]  # context + text
        embeddings = model.encode(texts, show_progress_bar=False)
        # ... store
```

---

## 5. Strategy Detection Logic

Setiap buku melewati decision tree berikut:

```
                              RAW TEXT
                                 │
                                 ▼
                    ┌─────────────────────┐
                    │  Pre-filter         │
                    │  (XML, empty H, img) │
                    └────────┬────────────┘
                             │
                             ▼
                    ┌─────────────────────┐
                    │  Hitung metrik      │
                    │  heading_count       │
                    │  heading_density     │
                    │  h4_ratio            │
                    │  xml_artifacts       │
                    │  avg_para_length     │
                    └────────┬────────────┘
                             │
                             ▼
                    ┌─────────────────────┐
                    │  LLM ANALYSIS       │
                    │  (Free Reasoning API)│
                    └────────┬────────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
     │ heading_based│ │   hybrid    │ │  recursive   │
     │              │ │              │ │              │
     │ H density >  │ │ H density    │ │ H density = 0│
     │ 0.03         │ │ 0.001-0.03  │ │              │
     │              │ │              │ │              │
     │ Split di H   │ │ Heading split│ │ Recursive    │
     │ H1/H2/H3/H4 │ │ + semantic   │ │ char split   │
     │              │ │ fallback     │ │ (LangChain)  │
     └──────────────┘ └──────────────┘ └──────────────┘
              │              │              │
              └──────┬───────┘              │
                     ▼                      │
            ┌──────────────────┐            │
            │ POST-PROCESS     │◄───────────┘
            │                  │
            │ - Split oversized│
            │   (Semantic GPU) │
            │ - Merge tiny     │
            │ - Merge similar  │
            │   (Semantic GPU) │
            └──────────────────┘
```

### Strategy Decision Matrix

| **Kondisi** | **Strategi** | **H4 Boundary?** | **Contoh Buku** |
|---|---|---|---|
| Heading density > 0.05 & H4 < 30% | `heading_based` | Tidak | Robert McKee's Story |
| Heading density > 0.05 & H4 > 30% | `heading_based` | Ya | Save The Cat, Hero 1000 Faces |
| Heading density 0.01–0.05 | `hybrid` | Sesuai rasio | Building a StoryBrand |
| Heading density < 0.01 & > 0 | `hybrid` | Ya | On Writing (after cleanup) |
| Heading density = 0 | `recursive` | N/A | Plain text, no structure |
| XML artifacts > 5 | `needs_cleanup_first` | N/A | Story Genius (raw) |

---

## 6. Hardware Utilization Map

```
                  CPU (Ryzen 9 7900X)      GPU (16GB VRAM)         LLM API (Free Reasoning)
                ┌──────────────────────┐ ┌────────────────────┐ ┌────────────────────────┐
  Layer 1       │  OCR Processing      │ │  OCR Acceleration  │ │                        │
  Extraction    │  (marker-pdf)        │ │  (marker-pdf CUDA) │ │  (optional enhancement)│
                └──────────────────────┘ └────────────────────┘ └────────────────────────┘
                ┌──────────────────────┐ ┌────────────────────┐ ┌────────────────────────┐
  Layer 2       │  Regex pre-clean     │ │                    │ │  Deep-clean analysis   │
  Cleanup       │  (0.01 detik)        │ │                    │ │  (1-2 calls per buku)  │
                └──────────────────────┘ └────────────────────┘ └────────────────────────┘
                ┌──────────────────────┐ ┌────────────────────┐ ┌────────────────────────┐
  Layer 3       │  Heuristic fallback  │ │                    │ │  Strategy recommend    │
  Analyzer      │  (0.001 detik)       │ │                    │ │  (1 call per buku)     │
                └──────────────────────┘ └────────────────────┘ └────────────────────────┘
                ┌──────────────────────┐ ┌────────────────────┐ ┌────────────────────────┐
  Layer 4       │  Heading split       │ │                    │ │                        │
  Structural    │  (0.1 detik)         │ │                    │ │                        │
                └──────────────────────┘ └────────────────────┘ └────────────────────────┘
                ┌──────────────────────┐ ┌────────────────────┐ ┌────────────────────────┐
  Layer 5       │                      │ │  BGE-M3 via CUDA   │ │                        │
  Refiner       │                      │ │  (10-30 detik)     │ │                        │
                └──────────────────────┘ └────────────────────┘ └────────────────────────┘
                ┌──────────────────────┐ ┌────────────────────┐ ┌────────────────────────┐
  Layer 6       │                      │ │                    │ │  Context generation    │
  Enhancer      │                      │ │                    │ │  (batch 10 chunks/call)│
                └──────────────────────┘ └────────────────────┘ └────────────────────────┘
                ┌──────────────────────┐ ┌────────────────────┐ ┌────────────────────────┐
  Layer 7       │                      │ │  BGE-M3 via CUDA   │ │                        │
  Embedding     │                      │ │  (30 detik-2 mnt)  │ │                        │
                └──────────────────────┘ └────────────────────┘ └────────────────────────┘
```

### Resource Budget per Buku (avg 500K chars)

| **Resource** | **Layer 2** | **Layer 3** | **Layer 5** | **Layer 6** | **Layer 7** | **Total** |
|---|---|---|---|---|---|---|
| CPU time | 0.01s | — | — | — | — | **0.01s** |
| GPU time | — | — | 20s | — | 60s | **80s** |
| LLM calls | 2 | 1 | — | 10 | — | **13 calls** |
| VRAM used | — | — | ~4GB | — | ~4GB | **~4GB** |

---

## 7. Module Structure

```
forge/
├── plan.md                         ← This file
│
├── arcwright/                       ← Existing package
│   ├── __init__.py
│   ├── config.py                    ← Refactor: tambah GPU/LLM config
│   ├── extract.py                   ← Existing (no change)
│   │
│   ├── cleanup.py                   ← 🆕 NEW: Layer 2
│   │   ├── clean_markdown()
│   │   ├── _pre_clean_regex()
│   │   └── _deep_clean_llm()
│   │
│   ├── strategy.py                  ← 🆕 NEW: Layer 3
│   │   ├── analyze_structure()
│   │   ├── analyze_llm()
│   │   ├── analyze_offline()
│   │   └── detect_strategy()
│   │
│   ├── chunk.py                     ← REFACTOR: Layer 4
│   │   ├── chunk_markdown()
│   │   ├── chunk_by_headings()
│   │   ├── chunk_recursive()
│   │   └── get_chunk_stats()
│   │
│   ├── refiner.py                   ← 🆕 NEW: Layer 5
│   │   ├── SemanticRefiner
│   │   │   ├── split_oversized()
│   │   │   ├── merge_similar_adjacent()
│   │   │   └── compute_coherence()
│   │   └── batch_refine()
│   │
│   ├── enhancer.py                  ← 🆕 NEW: Layer 6
│   │   ├── enhance_chunks()
│   │   ├── _generate_summary()
│   │   └── _enhance_batch()
│   │
│   └── embed.py                     ← REFACTOR: Layer 7
│       ├── get_embedding_model()
│       ├── embed_and_store()
│       └── list_collections()
│
├── scripts/                         ← RUNNABLE SCRIPTS
│   ├── run-pipeline.py              ← Full pipeline (all 7 layers)
│   ├── run-cleanup.py               ← Layer 2 only
│   ├── run-analyze.py               ← Layer 3 only (test strategy)
│   ├── run-chunk.py                 ← Layer 4 only
│   ├── run-refine.py                ← Layer 5 only (GPU)
│   ├── run-enhance.py               ← Layer 6 only
│   └── run-embed.py                 ← Layer 7 only
│
├── output/                          ← Existing output
│   └── ...
│
└── data/                            ← Existing data
    └── ...
```

### Package (Reusable)

```
chunking-engine/                     ← 🆕 NEW: pip-installable package
├── pyproject.toml
├── src/
│   └── chunking_engine/
│       ├── __init__.py
│       ├── core/
│       │   ├── cleanup.py           ← Mirip forge version
│       │   ├── strategy.py
│       │   ├── chunk.py
│       │   ├── refiner.py
│       │   ├── enhancer.py
│       │   └── embed.py
│       ├── utils/
│       │   ├── text_utils.py
│       │   └── stats.py
│       └── cli.py                  ← CLI entry point
├── tests/
└── README.md
```

---

## 8. Implementation Roadmap

### Phase 1: Core Fixes (Priority 🔴)

**Target:** Fix 80% masalah chunking tanpa GPU/LLM

| **Task** | **File** | **Est.** | **Detail** |
|---|---|---|---|
| 1.1 Pre-filter regex | `cleanup.py` | 15 menit | XML, empty H, image refs |
| 1.2 H4 boundary support | `chunk.py` | 10 menit | Configurable heading levels |
| 1.3 Post-processor | `chunk.py` | 15 menit | Merge tiny, split oversized |
| 1.4 Config refactor | `config.py` | 10 menit | GPU/LLM flags, paths |

**Deliverable:** All 10 books re-chunk dengan kualitas lebih baik, tanpa GPU/LLM

### Phase 2: GPU Semantic Refiner (Priority 🟡)

**Target:** Chunk quality naik drastis via GPU

| **Task** | **File** | **Est.** | **Detail** |
|---|---|---|---|
| 2.1 `SemanticRefiner` class | `refiner.py` | 45 menit | GPU init, batch embed |
| 2.2 `split_oversized()` | `refiner.py` | 30 menit | Topic shift detection |
| 2.3 `merge_similar()` | `refiner.py` | 20 menit | Adjacent similarity merge |
| 2.4 Integrasi ke pipeline | `pipeline.py` | 15 menit | Call refiner between chunk & embed |

**Deliverable:** Chunk oversized dipecah secara cerdas, chunk redundan di-merge

### Phase 3: LLM Strategy Analyzer (Priority 🟢)

**Target:** Adaptive chunking per buku

| **Task** | **File** | **Est.** | **Detail** |
|---|---|---|---|
| 3.1 LLM client wrapper | `utils/llm.py` | 20 menit | Free Reasoning API handler |
| 3.2 `analyze_llm()` | `strategy.py` | 30 menit | Prompt + JSON parser |
| 3.3 `analyze_offline()` | `strategy.py` | 15 menit | Heuristic fallback |
| 3.4 Integrasi ke pipeline | `pipeline.py` | 10 menit | Call analyzer before chunk |

**Deliverable:** Setiap buku otomatis dianalisis & dapet strategi optimal

### Phase 4: LLM Contextual Enhancer (Priority 🔵)

**Target:** Embedding berkualitas tinggi dengan konteks

| **Task** | **File** | **Est.** | **Detail** |
|---|---|---|---|
| 4.1 `_generate_summary()` | `enhancer.py` | 15 menit | Ringkasan global buku |
| 4.2 `enhance_chunks()` | `enhancer.py` | 40 menit | Batch context generation |
| 4.3 Integrasi ke embed | `embed.py` | 10 menit | Context + text = input embedding |

**Deliverable:** Tiap chunk punya konteks posisi dalam dokumen

### Phase 5: Document Boundary Detection (Priority ⚪)

**Target:** Foreword, appendix, index tidak nyampur dengan konten utama

| **Task** | **File** | **Est.** | **Detail** |
|---|---|---|---|
| 5.1 Boundary prompt | `cleanup.py` | 20 menit | LLM prompt untuk deteksi section type |
| 5.2 Section tagger | `cleanup.py` | 20 menit | [SKIP]/[META]/[CONTENT] tagging |

### Phase 6: Refactor ke Package Reusable (Priority ⚪)

**Target:** `pip install chunking-engine` bisa dipake di project lain

| **Task** | **File** | **Est.** |
|---|---|---|
| 6.1 Extract core logic | `chunking-engine/` | 2 jam |
| 6.2 CLI entry point | `cli.py` | 30 menit |
| 6.3 Unit tests | `tests/` | 1 jam |
| 6.4 README + docs | `docs/` | 30 menit |

---

## 9. Reusability Design

### Usage in Arcwright

```python
from forge.arcwright.chunking import ChunkingEngine

engine = ChunkingEngine(
    use_gpu=True,           # GPU 16GB → CUDA
    use_llm=True,            # Free Reasoning API
    min_chars=150,
    max_chars=2500,
)

# Process single file
result = engine.process_file("buku.pdf")

# Process directory
results = engine.process_directory("./books/")

# Process raw text
result = engine.process_text(long_markdown_text)

# Get report
print(result.report())
```

### Usage in Other Projects

```bash
pip install chunking-engine
```

```python
from chunking_engine import ChunkingEngine

# Di project analisis berita
engine = ChunkingEngine(strategy="hybrid")
chunks = engine.process_text(article_text)

# Di project RAG perusahaan
engine = ChunkingEngine(use_gpu=True, use_llm=True)
chunks = engine.process_directory("./company_docs/")
```

### Design for Extensibility

```python
# User bisa kasi custom strategy
class CustomStrategy(ChunkingStrategy):
    def chunk(self, text: str) -> list:
        # Custom chunking logic
        pass

engine = ChunkingEngine()
engine.register_strategy("custom", CustomStrategy())
```

---

## 10. Appendices

### A. Performance Estimates

Semua angka berdasarkan resource: Ryzen 9 7900X · GPU 16GB VRAM · Free Reasoning API

| **Skenario** | **10 buku** | **29 buku** | **100 buku** |
|---|---|---|---|
| Phase 1 (CPU only) | 2 menit | 5 menit | 15 menit |
| Phase 2 (+ GPU) | 5 menit | 15 menit | 50 menit |
| Phase 3 (+ LLM analyzer) | 7 menit | 20 menit | 70 menit |
| Phase 4 (+ LLM enhancer) | 15 menit | 45 menit | 2.5 jam |
| Full pipeline | 20-30 menit | 1-2 jam | 5-6 jam |

### B. Expected Quality Improvement

| **Buku** | **Sekarang** | **Phase 1** | **Phase 2** | **Phase 3+4** |
|---|---|---|---|---|
| Building a StoryBrand | 77 chunks | 100+ | 120+ | 150+ |
| On Writing (Stephen King) | 4 chunks | 70+ 🚀 | 80+ | 100+ |
| Preview Contagious | 4 chunks | 4 (preview) | 4 | 4 |
| Robert McKee's Story | 265 chunks | 280+ | 350+ | 400+ |
| Save The Cat | 7 chunks | 50+ 🚀 | 60+ | 80+ |
| Story Genius | 2 chunks | 100+ 🚀 | 150+ | 200+ |
| Anatomy of Story | 37 chunks | 200+ 🚀 | 250+ | 300+ |
| Hero with 1000 Faces | 11 chunks | 100+ 🚀 | 150+ | 200+ |
| Science of Storytelling | 30 chunks | 60+ 🚀 | 80+ | 100+ |
| Wired for Story | 81 chunks | 100+ | 130+ | 150+ |
| **Total** | **518** | **~1,000** | **~1,500+** | **~1,800+** |

### C. Estimated LLM API Cost

Free Reasoning API — **gratis**. Yang dihabiskan cuma waktu processing.

| **Layer** | **Calls per buku** | **Total 29 buku** | **Token estimate** |
|---|---|---|---|
| Cleanup (Layer 2) | 1-2 | 29-58 | ~500K tokens |
| Strategy (Layer 3) | 1 | 29 | ~200K tokens |
| Enhancer (Layer 6) | ~10 | ~290 | ~3M tokens |
| **Total** | **~12** | **~348** | **~3.7M tokens** |

> Semua estimasi ini **1x jalan** pas indexing. Query harian tidak kena biaya ini.

### D. Dependencies

```toml
# pyproject.toml
[project]
dependencies = [
    # Core
    "sentence-transformers>=3.0.0",      # BGE-M3 embedding
    "chromadb>=0.5.0",                    # Vector DB
    "numpy>=1.24.0",                      # Vector ops
    "scikit-learn>=1.3.0",               # Similarity metrics
    
    # GPU (optional — auto-detect)
    "torch>=2.0.0",                       # CUDA support
    
    # LLM (optional — pilih salah satu)
    "openai>=1.0.0",                      # OpenAI-compatible API
    
    # Extraction
    "marker-pdf>=1.0.0",                  # PDF OCR
    "ebooklib>=0.18",                     # EPUB
    "markdownify>=0.11.0",                # HTML→MD
    "beautifulsoup4>=4.12.0",             # HTML parser
    "python-docx>=1.1.0",                 # DOCX
]
```

---

> **Document version:** 1.0  
> **Last updated:** 2026-07-13  
> **Author:** Yui (for Arcwright Project)
