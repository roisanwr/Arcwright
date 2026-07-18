#!/usr/bin/env python3
"""Build Arcwright pitch deck with morph-3d transitions."""

import subprocess, os, time

WORKDIR = "/home/rois/Arcwright/pitchdeck"
MODEL = "model.glb"
FILE = "arcwright-pitch-deck.pptx"
MODEL_PATH = os.path.join(WORKDIR, MODEL)
FILE_PATH = os.path.join(WORKDIR, FILE)

def run(cmd, check=True):
    full = f"export PATH=\"$HOME/.local/bin:$PATH\" && cd {WORKDIR} && {cmd}"
    print(f"  {cmd[:80]}...")
    r = subprocess.run(full, shell=True, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        out = r.stdout.strip()[:100]
        err = r.stderr.strip()[:100]
        print(f"  ERR({r.returncode}): {out} {err}")
        if check:
            raise Exception(f"Command failed: {cmd[:60]}")
    return r

# Colors
DARK = "2D1B69"
WARM = "E8C547"
TEAL = "1A936F"
WHITE = "FFFFFF"
LIGHT_BG = "F5F3FF"
MUTED = "8B7E9B"
TEXT_DARK = "1A1025"

# Start fresh
if os.path.exists(FILE_PATH):
    os.remove(FILE_PATH)

# Create blank pptx
print("=== CREATE FILE ===")
run(f'officecli create "{FILE_PATH}"')

# === SLIDE 1: COVER ===
print("=== SLIDE 1: COVER ===")
run(f'officecli add "{FILE_PATH}" / --type slide --prop layout=blank --prop background={DARK}')
# Brand band
run(f'officecli add "{FILE_PATH}" /slide[1] --type shape --prop name=BrandBand --prop geometry=rect --prop fill={WARM} --prop x=0cm --prop y=18.5cm --prop width=33.87cm --prop height=0.55cm')
run(f"officecli add \"{FILE_PATH}\" /slide[1] --type shape --prop name=CoverTitle --prop text='Arcwright' --prop x=2cm --prop y=5cm --prop width=29.87cm --prop height=3cm --prop font=Georgia --prop size=44 --prop bold=true --prop color={WHITE} --prop align=center --prop fill=none")
run(f"officecli add \"{FILE_PATH}\" /slide[1] --type shape --prop name=Tagline --prop text='Storytelling AI \u2014 Everyone has a story. We help you tell it.' --prop x=2cm --prop y=8.5cm --prop width=29.87cm --prop height=1.5cm --prop font=Calibri --prop size=20 --prop color={WARM} --prop align=center --prop fill=none")
run(f"officecli add \"{FILE_PATH}\" /slide[1] --type shape --prop name=CoverMeta --prop text='Pre-Seed \u00b7 $500K \u00b7 July 2026' --prop x=2cm --prop y=15cm --prop width=29.87cm --prop height=1.2cm --prop font=Calibri --prop size=16 --prop color={WHITE} --prop align=center --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[1] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=7cm --prop y=0.5cm --prop width=20cm --prop height=17cm --prop roty=30 --prop rotx=8')

print("=== SLIDES 2-12: CREATE ===")
for i in range(12):
    bg = LIGHT_BG if i % 2 == 0 else WHITE
    run(f'officecli add "{FILE_PATH}" / --type slide --prop layout=blank --prop background={bg}')

print("=== SLIDE 2: PROBLEM ===")
run(f"officecli add \"{FILE_PATH}\" /slide[2] --type shape --prop name=P2Title --prop text='Most people have stories they never tell' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=36 --prop bold=true --prop color={DARK} --prop fill=none")
for card_idx, (x_pos, num, label) in enumerate([
    (1.5, "73%", "of people feel their life stories arent worth telling"),
    (12.04, "3.2B", "social media users hungry for authentic content daily"),
    (22.58, "85%", "of aspiring creators run out of story ideas within 3 months"),
]):
    run(f'officecli add "{FILE_PATH}" /slide[2] --type shape --prop geometry=roundRect --prop fill={LIGHT_BG} --prop x={x_pos}cm --prop y=5cm --prop width=9.78cm --prop height=10cm')
    run(f'officecli add "{FILE_PATH}" /slide[2] --type shape --prop text="{num}" --prop x={x_pos}cm --prop y=6cm --prop width=9.78cm --prop height=3cm --prop font=Georgia --prop size=60 --prop bold=true --prop color={DARK} --prop align=center --prop fill=none')
    run(f"officecli add \"{FILE_PATH}\" /slide[2] --type shape --prop text='{label}' --prop x={x_pos}cm --prop y=9.5cm --prop width=9.78cm --prop height=3cm --prop font=Calibri --prop size=16 --prop color={TEXT_DARK} --prop align=center --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[2] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=17cm --prop y=2cm --prop width=14cm --prop height=13cm --prop roty=80 --prop rotx=0')

print("=== SLIDE 3: SOLUTION ===")
run(f"officecli add \"{FILE_PATH}\" /slide[3] --type shape --prop name=P3Title --prop text='Arcwright: Your personal story discovery engine' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=32 --prop bold=true --prop color={DARK} --prop fill=none")
for idx, (title, desc) in enumerate([("1. Mine", "AI asks smart questions to uncover hidden stories from your life experiences"), ("2. Craft", "8 specialist agents collaborate to structure your narrative with proven storytelling frameworks"), ("3. Share", "Export ready-to-publish scripts for YouTube, TikTok, Podcast, or Blog")]):
    y = 4.5 + idx * 4.5
    run(f'officecli add "{FILE_PATH}" /slide[3] --type shape --prop geometry=roundRect --prop fill={LIGHT_BG} --prop x=1.5cm --prop y={y}cm --prop width=30.87cm --prop height=3.5cm')
    run(f"officecli add \"{FILE_PATH}\" /slide[3] --type shape --prop text='{title}' --prop x=3cm --prop y={y+0.3}cm --prop width=5cm --prop height=1.5cm --prop font=Georgia --prop size=24 --prop bold=true --prop color={DARK} --prop fill=none")
    run(f"officecli add \"{FILE_PATH}\" /slide[3] --type shape --prop text='{desc}' --prop x=3cm --prop y={y+2}cm --prop width=28cm --prop height=1.5cm --prop font=Calibri --prop size=16 --prop color={TEXT_DARK} --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[3] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=1cm --prop y=1cm --prop width=8cm --prop height=7cm --prop roty=220 --prop rotx=10')

print("=== SLIDE 4: MARKET ===")
run(f"officecli add \"{FILE_PATH}\" /slide[4] --type shape --prop name=P4Title --prop text='Market: $12B digital storytelling opportunity' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=36 --prop bold=true --prop color={DARK} --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[4] --type chart --prop chartType=bar --prop series1.name="USD (billions)" --prop series1.values="12,2.4,0.36" --prop series1.color={DARK} --prop categories="TAM,SAM,SOM (5-yr)" --prop x=2cm --prop y=4cm --prop width=20cm --prop height=12cm --prop title="Digital storytelling market sizing"')
run(f"officecli add \"{FILE_PATH}\" /slide[4] --type shape --prop text='Source: Grand View Research 2025 \u2014 Content creation platforms; SAM = 20% of TAM (AI-assisted market); SOM = 3% of SAM (Indonesia-first)' --prop x=2cm --prop y=16.5cm --prop width=29.87cm --prop height=2cm --prop font=Calibri --prop size=12 --prop italic=true --prop color={MUTED} --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[4] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=-2cm --prop y=-2cm --prop width=28cm --prop height=22cm --prop roty=120 --prop rotx=35')

print("=== SLIDE 5: PRODUCT ===")
run(f"officecli add \"{FILE_PATH}\" /slide[5] --type shape --prop name=P5Title --prop text='8 specialist agents, one Story Director' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=36 --prop bold=true --prop color={DARK} --prop fill=none")
for idx, (name, role) in enumerate([("Story Director", "Orchestrator"), ("Story Miner", "Interviewer"), ("RAG Librarian", "Knowledge"), ("Web Researcher", "Trends"), ("Validator", "Quality Gate"), ("Deep Dive", "Perspectives"), ("Outline Writer", "Structure"), ("Script Writer", "Narrative")]):
    col = idx % 4; row = idx // 4
    x = 1.5 + col * 7.9; y = 4.5 + row * 6.5
    run(f'officecli add "{FILE_PATH}" /slide[5] --type shape --prop geometry=roundRect --prop fill={LIGHT_BG} --prop line=none --prop x={x}cm --prop y={y}cm --prop width=7.2cm --prop height=5.5cm')
    run(f"officecli add \"{FILE_PATH}\" /slide[5] --type shape --prop text='{name}' --prop x={x}cm --prop y={y+0.5}cm --prop width=7.2cm --prop height=1.5cm --prop font=Georgia --prop size=18 --prop bold=true --prop color={DARK} --prop align=center --prop fill=none")
    run(f"officecli add \"{FILE_PATH}\" /slide[5] --type shape --prop text='{role}' --prop x={x}cm --prop y={y+2.5}cm --prop width=7.2cm --prop height=1.5cm --prop font=Calibri --prop size=16 --prop color={MUTED} --prop align=center --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[5] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=-3cm --prop y=-2cm --prop width=30cm --prop height=24cm --prop roty=170 --prop rotx=-20')

print("=== SLIDE 6: WHY NOW ===")
run(f"officecli add \"{FILE_PATH}\" /slide[6] --type shape --prop name=P6Title --prop text='Why now: three converging trends' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=36 --prop bold=true --prop color={DARK} --prop fill=none")
for idx, (title, stat, desc) in enumerate([("LLM Cost Collapse", "-90%", "Inference costs dropped 90% since 2024"), ("Content Demand Boom", "3.2B", "Social media content consumers growing 18% YoY"), ("RAG Maturity", "9,270", "ChromaDB + BGE-M3 knowledge pipeline production-ready")]):
    x = 1.5 + idx * 10.95
    run(f'officecli add "{FILE_PATH}" /slide[6] --type shape --prop geometry=roundRect --prop fill={LIGHT_BG} --prop x={x}cm --prop y=5cm --prop width=9.78cm --prop height=12cm')
    run(f"officecli add \"{FILE_PATH}\" /slide[6] --type shape --prop text='{title}' --prop x={x}cm --prop y=5.5cm --prop width=9.78cm --prop height=1.5cm --prop font=Calibri --prop size=22 --prop bold=true --prop color={DARK} --prop align=center --prop fill=none")
    run(f'officecli add "{FILE_PATH}" /slide[6] --type shape --prop text="{stat}" --prop x={x}cm --prop y=7.5cm --prop width=9.78cm --prop height=3cm --prop font=Georgia --prop size=60 --prop bold=true --prop color={TEAL} --prop align=center --prop fill=none')
    run(f"officecli add \"{FILE_PATH}\" /slide[6] --type shape --prop text='{desc}' --prop x={x}cm --prop y=11.5cm --prop width=9.78cm --prop height=4cm --prop font=Calibri --prop size=16 --prop color={TEXT_DARK} --prop align=center --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[6] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=18cm --prop y=-1cm --prop width=24cm --prop height=22cm --prop roty=45 --prop rotx=5')

print("=== SLIDE 7: TRACTION ===")
run(f"officecli add \"{FILE_PATH}\" /slide[7] --type shape --prop name=P7Title --prop text='Traction: RAG pipeline live, agents building' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=32 --prop bold=true --prop color={DARK} --prop fill=none")
for idx, (num, label) in enumerate([("9,270", "Knowledge chunks"), ("1.0", "Prototype deadline"), ("3/3", "Phases planned")]):
    x = 1.5 + idx * 10.95
    run(f'officecli add "{FILE_PATH}" /slide[7] --type shape --prop geometry=roundRect --prop fill={DARK} --prop x={x}cm --prop y=5cm --prop width=9.78cm --prop height=5cm')
    run(f'officecli add "{FILE_PATH}" /slide[7] --type shape --prop text="{num}" --prop x={x}cm --prop y=5.5cm --prop width=9.78cm --prop height=2.5cm --prop font=Georgia --prop size=48 --prop bold=true --prop color={WARM} --prop align=center --prop fill=none')
    run(f"officecli add \"{FILE_PATH}\" /slide[7] --type shape --prop text='{label}' --prop x={x}cm --prop y=8cm --prop width=9.78cm --prop height=1.5cm --prop font=Calibri --prop size=16 --prop color={WHITE} --prop align=center --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[7] --type shape --prop geometry=roundRect --prop fill={LIGHT_BG} --prop x=1.5cm --prop y=12cm --prop width=30.87cm --prop height=5cm')
run(f"officecli add \"{FILE_PATH}\" /slide[7] --type shape --prop text='Phase 1: RAG Pipeline \u2014 100% complete \u00b7 Phase 2: LangGraph Agents \u2014 In progress (8 agents)' --prop x=2.5cm --prop y=13cm --prop width=28cm --prop height=3cm --prop font=Calibri --prop size=18 --prop bold=true --prop color={DARK} --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[7] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=1cm --prop y=2cm --prop width=15cm --prop height=14cm --prop roty=330 --prop rotx=8')

print("=== SLIDE 8: BUSINESS MODEL ===")
run(f"officecli add \"{FILE_PATH}\" /slide[8] --type shape --prop name=P8Title --prop text='Business model: Freemium SaaS' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=36 --prop bold=true --prop color={DARK} --prop fill=none")
for idx, (name, price, features) in enumerate([("Free", "$0", "3 stories/mo \u00b7 Basic frameworks \u00b7 Single platform"), ("Pro", "$9.99/mo", "Unlimited \u00b7 All 29 frameworks \u00b7 4 platforms \u00b7 Priority")]):
    x = 1.5 + idx * 16.5; bg = DARK if idx == 1 else LIGHT_BG; tc = WHITE if idx == 1 else DARK
    run(f'officecli add "{FILE_PATH}" /slide[8] --type shape --prop geometry=roundRect --prop fill={bg} --prop x={x}cm --prop y=5cm --prop width=15cm --prop height=11cm')
    run(f"officecli add \"{FILE_PATH}\" /slide[8] --type shape --prop text='{name}' --prop x={x}cm --prop y=5.5cm --prop width=15cm --prop height=1.5cm --prop font=Georgia --prop size=28 --prop bold=true --prop color={tc} --prop align=center --prop fill=none")
    run(f"officecli add \"{FILE_PATH}\" /slide[8] --type shape --prop text='{price}' --prop x={x}cm --prop y=7.5cm --prop width=15cm --prop height=2.5cm --prop font=Georgia --prop size=48 --prop bold=true --prop color={WARM} --prop align=center --prop fill=none")
    run(f"officecli add \"{FILE_PATH}\" /slide[8] --type shape --prop text='{features}' --prop x={x}cm --prop y=10.5cm --prop width=15cm --prop height=4cm --prop font=Calibri --prop size=16 --prop color={tc} --prop align=center --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[8] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=18cm --prop y=2cm --prop width=13cm --prop height=12cm --prop roty=100 --prop rotx=0')

print("=== SLIDE 9: TEAM ===")
run(f"officecli add \"{FILE_PATH}\" /slide[9] --type shape --prop name=P9Title --prop text='Founder: Built Arcwright solo, full-stack AI engineer' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=32 --prop bold=true --prop color={DARK} --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[9] --type shape --prop geometry=roundRect --prop fill={LIGHT_BG} --prop x=2cm --prop y=5cm --prop width=29.87cm --prop height=12cm')
run(f"officecli add \"{FILE_PATH}\" /slide[9] --type shape --prop text='roisanwr' --prop x=14cm --prop y=5.5cm --prop width=16cm --prop height=2cm --prop font=Georgia --prop size=28 --prop bold=true --prop color={DARK} --prop fill=none")
run(f"officecli add \"{FILE_PATH}\" /slide[9] --type shape --prop text='Founder & CEO' --prop x=14cm --prop y=7.5cm --prop width=16cm --prop height=1.5cm --prop font=Calibri --prop size=20 --prop color={MUTED} --prop fill=none")
for idx, ach in enumerate(["Built Arcwright Forge - 9,270-chunk RAG pipeline with ChromaDB + BGE-M3", "Integrated Hermes Agent multi-agent orchestration stack", "Full-stack: Python, LangGraph, FastAPI, React, ChromaDB", "Phase 1 complete in 2 weeks - solo execution to deadline"]):
    y = 9.5 + idx * 1.8
    run(f"officecli add \"{FILE_PATH}\" /slide[9] --type shape --prop text='> {ach}' --prop x=14cm --prop y={y}cm --prop width=16cm --prop height=1.5cm --prop font=Calibri --prop size=16 --prop color={TEXT_DARK} --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[9] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=8cm --prop y=1cm --prop width=18cm --prop height=16cm --prop roty=290 --prop rotx=5')

print("=== SLIDE 10: COMPETITIVE ===")
run(f"officecli add \"{FILE_PATH}\" /slide[10] --type shape --prop name=P10Title --prop text='Competitive landscape' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=36 --prop bold=true --prop color={DARK} --prop fill=none")
run(f"officecli add \"{FILE_PATH}\" /slide[10] --type table --prop data='Competitor,AI Story Mining,Multi-Agent,Story Frameworks RAG,Platform Export;ChatGPT,Partial,No,No,Text only;Jasper AI,No,No,Limited,Blog only;Copy.ai,No,No,No,Social only;Arcwright,Yes,Yes (8 agents),Yes (29 books),4 platforms' --prop style=medium1 --prop headerFill={DARK} --prop x=1.5cm --prop y=4cm --prop width=30.87cm --prop height=14cm")
run(f'officecli add "{FILE_PATH}" /slide[10] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=24cm --prop y=10cm --prop width=9cm --prop height=8cm --prop roty=270 --prop rotx=10')

print("=== SLIDE 11: FINANCIALS ===")
run(f"officecli add \"{FILE_PATH}\" /slide[11] --type shape --prop name=P11Title --prop text='Financial projections: $0 to $1.2M ARR in 3 years' --prop x=1.5cm --prop y=1.2cm --prop width=30.87cm --prop height=2.5cm --prop font=Georgia --prop size=32 --prop bold=true --prop color={DARK} --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[11] --type chart --prop chartType=column --prop series1.name="Revenue ($K)" --prop series1.values="0,120,480,1200" --prop series1.color={DARK} --prop series2.name="Users (K)" --prop series2.values="0,5,20,50" --prop series2.color={TEAL} --prop categories="Y0 (Launch),Y1,Y2,Y3" --prop x=1.5cm --prop y=4cm --prop width=20cm --prop height=13cm --prop title="3-year projection - Seed to Series A"')
run(f'officecli add "{FILE_PATH}" /slide[11] --type shape --prop geometry=roundRect --prop fill={LIGHT_BG} --prop line=none --prop x=22.5cm --prop y=4cm --prop width=9.8cm --prop height=13cm')
run(f"officecli add \"{FILE_PATH}\" /slide[11] --type shape --prop text='Key Assumptions' --prop x=23cm --prop y=4.5cm --prop width=8.8cm --prop height=1.2cm --prop font=Georgia --prop size=18 --prop bold=true --prop color={DARK} --prop fill=none")
for idx, a in enumerate(["5% free to Pro conversion rate", "$9.99/mo avg Pro ARPU", "30% YoY organic user growth", "85% gross margin (SaaS)", "12-month CAC payback"]):
    run(f"officecli add \"{FILE_PATH}\" /slide[11] --type shape --prop text='> {a}' --prop x=23cm --prop y={6+idx*1.8}cm --prop width=8.8cm --prop height=1.5cm --prop font=Calibri --prop size=14 --prop color={TEXT_DARK} --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[11] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=7cm --prop y=0.5cm --prop width=20cm --prop height=17cm --prop roty=30 --prop rotx=8')

print("=== SLIDE 12: ASK ===")
run(f"officecli add \"{FILE_PATH}\" /slide[12] --type shape --prop text='$500K' --prop x=2cm --prop y=2cm --prop width=29.87cm --prop height=5cm --prop font=Georgia --prop size=96 --prop bold=true --prop color={WHITE} --prop align=center --prop fill=none")
run(f"officecli add \"{FILE_PATH}\" /slide[12] --type shape --prop name=AskLabel --prop text='Pre-Seed \u00b7 18-month runway to Series A' --prop x=2cm --prop y=7cm --prop width=29.87cm --prop height=2cm --prop font=Calibri --prop size=24 --prop color={WARM} --prop align=center --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[12] --type chart --prop chartType=pie --prop series1.name="Use of Funds" --prop series1.values="50,30,12,8" --prop categories="Engineering,Go-to-Market,G&A,Reserve" --prop colors="{WARM},{TEAL},{LIGHT_BG},{WHITE}" --prop x=6cm --prop y=10cm --prop width=12cm --prop height=8cm --prop title="Use of Funds"')
run(f"officecli add \"{FILE_PATH}\" /slide[12] --type shape --prop text='Next milestone: 10K MAU \u00b7 $120K ARR \u00b7 Series A Q4 2027' --prop x=2cm --prop y=18cm --prop width=29.87cm --prop height=1.5cm --prop font=Calibri --prop size=18 --prop color={WHITE} --prop align=center --prop fill=none")
run(f'officecli add "{FILE_PATH}" /slide[12] --type model3d --prop src={MODEL_PATH} --prop name=BrainStem --prop x=7cm --prop y=0.5cm --prop width=20cm --prop height=17cm --prop roty=30 --prop rotx=8')

# Close file
print("=== CLOSE ===")
run(f'officecli close "{FILE_PATH}"')

print("\n=== BUILD COMPLETE ===")
size = os.path.getsize(FILE_PATH) if os.path.exists(FILE_PATH) else 0
print(f"File: {FILE_PATH}")
print(f"Size: {size} bytes ({size/1024:.0f} KB)")
