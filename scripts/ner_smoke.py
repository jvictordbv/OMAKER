import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.ner import BiomedicalNER
ner = BiomedicalNER()
print(ner.pipe.model.config.id2label)
print(ner.extract("Aspirin prevents stroke. Chemotherapy treats the tumor but causes nausea."))