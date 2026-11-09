import json, sys, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
import os; sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---- fake Ollama --------------------------------------------------------------
CALLS = []
SCRIPT = []  # contents returned by /api/chat, in order
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _send(self, code, obj):
        b = json.dumps(obj).encode(); self.send_response(code)
        self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(b)))
        self.end_headers(); self.wfile.write(b)
    def do_GET(self): self._send(200, {"models": [{"name": "qwen3:8b"}]})
    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        CALLS.append(body); self._send(200, {"message": {"content": SCRIPT.pop(0)}})
srv = HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
HOST = f"http://127.0.0.1:{srv.server_port}"

from core.llm_client import OllamaClient, LLMError
c = OllamaClient("qwen3:8b", HOST); c.check()
# 1) think block + fenced JSON, then invalid -> retry -> valid
SCRIPT[:] = ['<think>hmm</think>```json\n{"a": 1}\n```']
assert c.chat_json("s", "u", {"type": "object"}) == {"a": 1}
assert CALLS[-1]["think"] is False and CALLS[-1]["options"]["num_ctx"] == 8192 and "format" in CALLS[-1]
SCRIPT[:] = ["not json at all", '{"ok": true}']
assert c.chat_json("s", "u", {"type": "object"}) == {"ok": True}
assert "not valid JSON" in CALLS[-1]["messages"][-1]["content"]
SCRIPT[:] = ["x", "y", "z"]
try: c.chat_json("s", "u", {}); raise SystemExit("should fail")
except LLMError: pass
try: OllamaClient("llama3", HOST).check(); raise SystemExit("should fail")
except LLMError as e: assert "ollama pull" in str(e)
print("llm_client OK")

# ---- pipeline with stub NER (no torch / owlready2 needed) ----------------------
from core.ner import Entity
from core import hybrid_engine as he

text = "Aspirin prevents stroke. Chemotherapy treats the tumor but causes nausea. Aspirin and fever were listed."
def ent(word, typ, nth=0):
    i = -1
    for _ in range(nth + 1): i = text.index(word, i + 1)
    return Entity(word, i, i + len(word), typ, 0.99)

class StubNER:
    def extract(self, _):
        return [ent("Aspirin","DRUG"), ent("stroke","DISEASE"), ent("Chemotherapy","DRUG"), ent("tumor","DISEASE"),
                ent("nausea","SYMPTOM"), ent("Aspirin","DRUG",1), ent("fever","SYMPTOM")]

# LLM answers, in call order: pair classification (no PURE checkpoint here), then taxonomy.
# Deliberately includes bad output: a class named like an entity, an unknown parent, a cycle,
# a Drug entity put under a Disease subclass, and a disjoint group of ancestor/descendant.
pairs_answer = json.dumps({"results": [
    {"id": 0, "relation": "prevents"},   # Aspirin -> stroke
    {"id": 1, "relation": "treats"},     # Chemotherapy -> tumor
    {"id": 2, "relation": "causes"},     # Chemotherapy -> nausea
    {"id": 3, "relation": "treats"},     # Aspirin -> fever (co-occurrence only, but the LLM said treats)
    {"id": 99, "relation": "causes"},    # out of range: must be ignored
]})
tax_answer = json.dumps({
  "classes": [{"name": "analgesic", "parent": "Drug"}, {"name": "Cancer", "parent": "Disease"},
              {"name": "Aspirin", "parent": "Analgesic"},          # duplicates an entity name
              {"name": "Weird", "parent": "DoesNotExist"},          # unknown parent
              {"name": "LoopA", "parent": "LoopB"}, {"name": "LoopB", "parent": "LoopA"},
              {"name": "Drug", "parent": "Thing"}],                 # redefining a base class
  "instances": [{"name": "Aspirin", "class": "Aspirin"}, {"name": "tumor", "class": "Cancer"},
                {"name": "Chemotherapy", "class": "Cancer"},        # wrong branch for a DRUG
                {"name": "ghost entity", "class": "Drug"}],         # not in NER list
  "disjoint": [["Analgesic", "Drug"], ["Analgesic", "Cancer"]],
})
SCRIPT[:] = [pairs_answer, tax_answer]
logs = []
he.HybridEngine.ENTITY_SOURCE = "ner"   # scenario 1: entities from the NER model only
tax, triples = he.HybridEngine.extrair(text, "qwen3:8b", 0.1, logs.append, ner=StubNER(), client=OllamaClient("qwen3:8b", HOST))
print("\n".join(logs))
print(json.dumps(tax, indent=1))
for t in triples: print(t)

assert tax["classes"]["Analgesic"] == "Drug"
assert "Aspirin" not in tax["classes"] and "Drug" not in tax["classes"]
assert tax["classes"]["Weird"] == "BiomedicalEntity"
assert tax["classes"]["LoopA"] == "BiomedicalEntity" or tax["classes"]["LoopB"] == "BiomedicalEntity"
assert tax["instances"]["Aspirin"] == "Analgesic"        # redirected to the entity-named class's parent
assert tax["instances"]["tumor"] == "Cancer"
assert tax["instances"]["Chemotherapy"] == "Drug"        # Cancer branch rejected for a DRUG
assert "ghost entity" not in tax["instances"]
assert tax["disjoint"] == [["Analgesic", "Cancer"]]
assert len(triples) == 3 and {t[2] for t in triples} == {"prevents", "treats", "causes"}
assert any("SKIP" in l and "tumor" in l for l in logs)   # DISEASE "treats" rejected by the domain filter
print("pipeline OK")


# ---- scenario 2: NER model misses entities, the LLM finds them (and invents one) ----
from core.llm_ner import extract_entities_llm, merge_entities

class WeakNER:   # like the real DistilBERT on short sentences: only drug names
    last_rejected = [("tumor", "Coreference", 0.92)]
    def extract(self, _): return [ent("Aspirin", "DRUG"), ent("Chemotherapy", "DRUG")]

llm_entities = json.dumps({"entities": [
    {"text": "Aspirin", "type": "DRUG"}, {"text": "stroke", "type": "DISEASE"},
    {"text": "chemotherapy", "type": "DRUG"}, {"text": "tumor", "type": "DISEASE"},
    {"text": "nausea", "type": "SYMPTOM"}, {"text": "fever", "type": "SYMPTOM"},
    {"text": "cancer", "type": "DISEASE"},                      # hallucinated: not in the text
    {"text": "ever", "type": "SYMPTOM"},                        # substring of "fever": must not match
]})
SCRIPT[:] = [llm_entities]
verified = extract_entities_llm(OllamaClient("qwen3:8b", HOST), text)
words = sorted(v.text.lower() for v in verified)
assert "cancer" not in words and "ever" not in words, words
assert words.count("aspirin") == 2 and {"stroke", "tumor", "nausea", "fever", "chemotherapy"} <= set(words)

merged = merge_entities(WeakNER().extract(text), verified)
assert not any(a.start < b.end and b.start < a.end for i, a in enumerate(merged) for b in merged[i + 1:])  # no overlaps

he.HybridEngine.ENTITY_SOURCE = "both"
SCRIPT[:] = [llm_entities, json.dumps({"results": []}), json.dumps({"classes": [], "instances": [], "disjoint": []})]
logs2 = []
tax2, triples2 = he.HybridEngine.extrair(text, "qwen3:8b", 0.1, logs2.append, ner=WeakNER(), client=OllamaClient("qwen3:8b", HOST))
assert any("6 unique entities" in l for l in logs2), logs2
assert any("ignored: 'tumor'" in l for l in logs2)
assert set(tax2["instances"]) == {"Aspirin", "stroke", "Chemotherapy", "tumor", "nausea", "fever"}
print("llm_ner OK")