# ============================================================
#  Arcwright — Windows Setup Script (PowerShell)
#  Jalankan: .\setup.ps1
# ============================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "  ===========================================" -ForegroundColor Cyan
Write-Host "   Arcwright — Setup Script (Windows)" -ForegroundColor Cyan
Write-Host "  ===========================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Cek Python version ─────────────────────────────────────
Write-Host "  [1/5] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ❌ Python tidak ditemukan. Install Python 3.12+ dari https://python.org" -ForegroundColor Red
    exit 1
}
Write-Host "  ✅ $pythonVersion" -ForegroundColor Green

# ── 2. Buat virtual environment ───────────────────────────────
Write-Host ""
Write-Host "  [2/5] Creating virtual environment..." -ForegroundColor Yellow

if (Test-Path ".venv") {
    Write-Host "  ⏩ .venv already exists — skipping creation" -ForegroundColor DarkGray
} else {
    python -m venv .venv
    Write-Host "  ✅ .venv created" -ForegroundColor Green
}

# ── 3. Aktifkan venv dan install dependencies ─────────────────
Write-Host ""
Write-Host "  [3/5] Installing root dependencies (LangGraph, agents)..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install --quiet --upgrade pip
& .\.venv\Scripts\pip.exe install --quiet -r requirements.txt
Write-Host "  ✅ Root dependencies installed" -ForegroundColor Green

Write-Host ""
Write-Host "  [3b/5] Installing forge dependencies (RAG pipeline)..." -ForegroundColor Yellow
& .\.venv\Scripts\pip.exe install --quiet -r forge\requirements.txt
Write-Host "  ✅ Forge dependencies installed" -ForegroundColor Green

# ── 4. Setup .env ─────────────────────────────────────────────
Write-Host ""
Write-Host "  [4/5] Checking .env configuration..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "  ⚠️  .env dibuat dari .env.example" -ForegroundColor Yellow
    Write-Host "  ➡️  WAJIB isi OPENAI_API_KEY di .env sebelum menjalankan!" -ForegroundColor Red
} else {
    $envContent = Get-Content ".env" | Where-Object { $_ -match "OPENAI_API_KEY=sk-" }
    if ($envContent) {
        Write-Host "  ✅ .env found with OPENAI_API_KEY" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  .env ada tapi OPENAI_API_KEY belum diisi" -ForegroundColor Yellow
        Write-Host "  ➡️  Edit .env dan isi OPENAI_API_KEY=sk-..." -ForegroundColor Red
    }
}

# ── 5. Smoke test — verifikasi import ─────────────────────────
Write-Host ""
Write-Host "  [5/5] Running import smoke test..." -ForegroundColor Yellow

$smokeTest = @"
import sys
try:
    from config.settings import get_llm_for_agent, CHROMA_DIR
    from agents.state import ArcwrightState
    from graph.pipeline import create_arcwright_graph, make_initial_state
    graph = create_arcwright_graph()
    print('PASS')
except Exception as e:
    print(f'FAIL: {e}')
    sys.exit(1)
"@

$result = & .\.venv\Scripts\python.exe -c $smokeTest 2>&1
if ($result -eq "PASS") {
    Write-Host "  ✅ Graph compiled successfully — semua agent terhubung!" -ForegroundColor Green
} else {
    Write-Host "  ❌ Smoke test failed:" -ForegroundColor Red
    Write-Host "     $result" -ForegroundColor Red
}

# ── ChromaDB check ─────────────────────────────────────────────
Write-Host ""
Write-Host "  [+] Checking ChromaDB status..." -ForegroundColor Yellow
if (Test-Path "forge\output\chroma_db") {
    $chromaCheck = @"
import chromadb
client = chromadb.PersistentClient(path='forge/output/chroma_db')
cols = client.list_collections()
print(f'Collections: {[c.name for c in cols]}')
for c in cols:
    try:
        print(f'  - {c.name}: {c.count()} chunks')
    except Exception as e:
        print(f'  - {c.name}: (error reading count - {e})')
"@
    & .\.venv\Scripts\python.exe -c $chromaCheck 2>&1
} else {
    Write-Host "  ⚠️  forge\output\chroma_db tidak ditemukan — RAG belum di-populate" -ForegroundColor Yellow
    Write-Host "  ➡️  Jalankan forge pipeline dulu untuk embed buku-buku" -ForegroundColor DarkGray
}

# ── Summary ────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ===========================================" -ForegroundColor Cyan
Write-Host "   Setup selesai! Cara menjalankan:" -ForegroundColor Cyan
Write-Host "  ===========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  # Aktifkan virtual env:" -ForegroundColor White
Write-Host "  .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
Write-Host ""
Write-Host "  # Jalankan CLI storytelling:" -ForegroundColor White
Write-Host "  python main.py --name 'NamaMu' --platform youtube" -ForegroundColor Green
Write-Host ""
Write-Host "  # Jalankan Forge API (RAG pipeline):" -ForegroundColor White
Write-Host "  python forge\api\main.py" -ForegroundColor Green
Write-Host ""
Write-Host "  # Jalankan Frontend (terminal terpisah):" -ForegroundColor White
Write-Host "  cd forge\frontend && npm install && npm run dev" -ForegroundColor Green
Write-Host ""
