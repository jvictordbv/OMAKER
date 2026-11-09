from core.ner import BiomedicalNER
ner = BiomedicalNER()
print(ner.pipe.model.config.id2label)
print(ner.extract("Aspirin prevents stroke. Chemotherapy treats the tumor but causes nausea."))