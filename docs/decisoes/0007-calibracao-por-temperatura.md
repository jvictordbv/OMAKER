# 0007. Calibração da confiança por temperatura

- **Status:** Aceita
- **Data:** 2026-11-24
- **Decidido por:** Gustavo

## Contexto

O pipeline descartava relações do PURE com confiança abaixo de 0,70 (`DEFAULT_CONFIDENCE_THRESHOLD`), como se a confiança fosse a probabilidade de acerto. Não era. No teste do BioRED, 328 das 385 previsões tinham confiança acima de 0,9, e só 73% delas estavam certas. O erro de calibração esperado (ECE, com 10 faixas) era de 0,271. Com o modelo confiante demais, o limite de 0,70 quase não filtrava nada.

## Decisão

- A confiança passa a ser `softmax(logits / T)`. A temperatura `T` é ajustada por máxima verossimilhança na **validação** (453 exemplos).
- O limite de confiança também é escolhido na validação, pelo micro-F1, numa grade de 0,30 a 0,95.
- O teste (385 exemplos) entra só no relatório.
- No checkpoint do BioRED: `T` = 4,33 e limite 0,35.
- A calibração fica num arquivo ao lado do checkpoint (`model.calibration.json`); o `model.pt` não muda. A carga do modelo lê o arquivo, se existir, e o pipeline usa o limite calibrado no lugar do 0,70. Sem o arquivo, nada muda.
- A calibração vale só para o modelo em que foi ajustada: instalar um modelo novo apaga a calibração antiga, e a instalação da calibração confere o sha256 do modelo.

## Alternativas consideradas

- **Manter o limite fixo de 0,70.** Filtra pouco e passa a ideia falsa de que 0,70 significa 70% de acerto.
- **Escolher só um limite novo, sem temperatura.** Mudaria o filtro, mas a confiança mostrada continuaria sem sentido.
- **Pesos por classe para reduzir os falsos positivos de `treats`.** Registrada como ideia; mexe no treino, não na leitura da confiança.

## Consequências

### Positivas

- A confiança passa a corresponder ao acerto: ECE no teste de 0,271 para 0,055. Na faixa de 0,8 a 0,9, por exemplo, a confiança média é 0,85 e o acerto 0,87.
- O ajuste é barato (53 s na CPU) e não exige treinar de novo.

### Negativas e riscos

- A extração não melhora: micro-F1 de 0,743 com o limite 0,70 e de 0,738 com o calibrado. A temperatura não muda a classe prevista, e o limite escolhido fica baixo.
- O limite de 0,35 está perto da ponta inferior da grade; quase toda previsão diferente de `no_relation` passa.
- A calibração herda o ruído do BioRED (rótulos por resumo) e foi medida só em pares químico e doença. Em texto de outro tipo, ela pode não valer.
- Hoje a confiança só aparece no log de cada axioma (`omaker/ontology/builder.py`); ela não é gravada na ontologia.

## Referências

- `omaker/relations/calibration.py` (`fit_temperature`, `ece`, `best_threshold`, `install`), `omaker/relations/model.py` (`load`), `omaker/pipeline/engine.py` (`_relations_pure`), `omaker/relations/train.py` (`--install`).
- Testes: `tests/test_calibration.py::test_ece_measures_overconfidence`, `tests/test_calibration.py::test_fit_temperature_recovers_overconfident_scale`, `tests/test_calibration.py::test_install_copies_calibration_only_to_the_same_model`, `tests/test_hybrid_engine.py::test_pure_uses_the_calibrated_threshold`, `tests/test_training.py::test_install_removes_a_stale_calibration`.
- [PR #17](https://github.com/jvictordbv/OMAKER/pull/17) (calibração), [PR #22](https://github.com/jvictordbv/OMAKER/pull/22) (instalação com a calibração certa).
- C. Guo et al., "On Calibration of Modern Neural Networks", ICML 2017.
- Notas internas do projeto: registro do experimento de calibração (2026-11-24), com o diagrama de confiabilidade antes e depois.
