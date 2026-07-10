# 🔧 Arcwright — Project Monorepo

> **Side project:** PDF Intelligence Pipeline (RAG system)  
> **Main project:** Storytelling AI — Multi-agent narrative system

---

## 📦 Structure

```
Arcwright/
├── forge/                       ← 🧪 RAG SIDE PROJECT (semua ada di sini)
│   ├── arcwright/               ← Python package (extract, chunk, embed, pipeline)
│   ├── api/                     ← FastAPI backend
│   ├── frontend/                ← React + Vite frontend
│   ├── src/                     ← Original pipeline scripts
│   ├── output/                  ← Generated outputs (chunks, chroma_db)
│   ├── data/                    ← PDF files & extracted text
│   ├── uploads/                 ← Temporary uploads
│   ├── requirements.txt         ← Python dependencies
│   └── README.md                ← 📚 Full RAG project docs
│
├── .bob/                        ← 🤖 IBM Bob project markers
├── AGENTS.md                    ← AI agent instructions
├── README.md                    ← This file (you are here)
└── venv/                        ← Virtual environment
```

---

## 🧪 RAG Pipeline — `forge/`

Semua kode RAG ada di **`forge/`** — lengkap dengan docs sendiri.

### Cara Cepet Jalanin

```bash
# 1. Aktifkan venv
cd ~/Arcwright
source venv/bin/activate

# 2. Start API backend
python forge/api/main.py
# → http://localhost:8765

# 3. Start frontend (terminal lain)
cd ~/Arcwright/forge/frontend
npm run dev
# → http://localhost:5173
```

> 📖 **Dokumentasi lengkap ada di:** [`forge/README.md`](./forge/README.md)  
> Mencakup: tech stack, architecture, API reference, frontend usage, Python library usage, output formats, OCR guide, FAQ, dan development guide.

---

## 🏗️ Main Project

Proyek utama Arcwright adalah **Storytelling AI** — multi-agent system untuk narrative generation.
(Lanjutan — folder utama untuk development lebih lanjut.)

---

*Built with ❤️ — RAG side project lives in `forge/`*
