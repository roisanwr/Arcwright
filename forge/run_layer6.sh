#!/usr/bin/env bash
# Layer 6: Contextual Enhancer — test with Pixar using Gemma 4:26b local
export LLM_API_URL="http://localhost:11434/v1"
export LLM_API_KEY="ollama"
export LLM_MODEL="gemma4:26b"

cd /home/rois/Arcwright
exec /home/rois/rag-storytelling/bin/python3 -c "
import os, sys, json, time
sys.path.insert(0, 'forge')
from arcwright import config
from arcwright.enhancer import ContextualEnhancer

target = 'refined_pixar_storytelling_rules_for_effective_sto'
base = config.OUTPUT_DIR

# Load chunks
cf = os.path.join(base, target, 'chunks_refined.json')
with open(cf) as f:
    chunks = json.load(f)

# Load cleaned text for doc summary
cleanf = os.path.join(base, target, 'cleaned.md')
with open(cleanf) as f:
    full_text = f.read()

print(f'Loaded {len(chunks)} chunks, full_text={len(full_text):,} chars')
print(f'LLM: {config.LLM_API_URL} / {config.LLM_MODEL}')
print()

enhancer = ContextualEnhancer(batch_size=10)
enhanced = enhancer.enhance_all(chunks, full_text)

# Save
out = os.path.join(base, target, 'chunks_enhanced.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(enhanced, f, indent=2, ensure_ascii=False)

# Stats
n_ctx = sum(1 for c in enhanced if c.get('_context'))
print(f'\nEnhanced: {n_ctx}/{len(enhanced)} chunks have context')

# Sample
print('\n=== SAMPLE (chunk 0) ===')
print(f'Before text: {chunks[0][\"text\"][:200]}...')
if enhanced[0].get('_context'):
    print(f'Context: {enhanced[0][\"_context\"]}')
    print(f'After text: {enhanced[0][\"text\"][:300]}...')
print()
# Sample middle chunk
mid = len(enhanced) // 2
print(f'=== SAMPLE (chunk {mid}) ===')
if enhanced[mid].get('_context'):
    print(f'Context: {enhanced[mid][\"_context\"]}')
    print(f'After text: {enhanced[mid][\"text\"][:200]}...')
"
