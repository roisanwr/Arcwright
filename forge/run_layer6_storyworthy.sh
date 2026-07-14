#!/usr/bin/env bash
# Layer 6: Contextual Enhancer — test with Storyworthy using local 9Router
export LLM_API_URL="http://0.0.0.0:20128/v1"
export LLM_API_KEY="sk-782161f8144ce425-lzjev3-4e325d13"
export LLM_MODEL="ag/gemini-3.1-pro-low"
export USE_LLM=True

cd /home/rois/Arcwright
exec /home/rois/rag-storytelling/bin/python3 -c "
import os, sys, json, time
sys.path.insert(0, 'forge')
from arcwright import config
from arcwright.enhancer import ContextualEnhancer

target = 'refined_storyworthy'
base = config.OUTPUT_DIR

cf = os.path.join(base, target, 'chunks_refined.json')
if not os.path.exists(cf):
    print(f'❌ File not found: {cf}')
    sys.exit(1)

with open(cf) as f:
    chunks = json.load(f)

cleanf = os.path.join(base, target, 'cleaned.md')
with open(cleanf) as f:
    full_text = f.read()

print(f'Loaded {len(chunks)} chunks, full_text={len(full_text):,} chars')
print(f'LLM: {os.environ.get(\"LLM_API_URL\")} / {os.environ.get(\"LLM_MODEL\")}')
print()

# Batch size 10 
enhancer = ContextualEnhancer(batch_size=10)

# Patch the LLM _call function inside the script to force stream=False
import arcwright.utils.llm as llm_module
original_call = llm_module._call

def patched_call(prompt, system=None):
    from openai import OpenAI
    client = OpenAI(
        api_key=os.environ.get('LLM_API_KEY'),
        base_url=os.environ.get('LLM_API_URL'),
    )
    messages = []
    if system:
        messages.append({'role': 'system', 'content': system})
    messages.append({'role': 'user', 'content': prompt})
    
    resp = client.chat.completions.create(
        model=os.environ.get('LLM_MODEL'),
        messages=messages,
        temperature=0.1,
        max_tokens=200,
        stream=False  # FORCE NON-STREAMING FOR 9ROUTER
    )
    return resp.choices[0].message.content.strip()

llm_module._call = patched_call

t0 = time.time()
enhanced = enhancer.enhance_all(chunks, full_text)
elapsed = time.time() - t0

# Save
out = os.path.join(base, target, 'chunks_enhanced.json')
with open(out, 'w', encoding='utf-8') as f:
    json.dump(enhanced, f, indent=2, ensure_ascii=False)

n_ctx = sum(1 for c in enhanced if c.get('_context'))
print(f'\nEnhanced: {n_ctx}/{len(enhanced)} chunks have context in {elapsed:.0f}s')
"
