# Contribuidores

## Autor

- **João Victor Ferreira Barbosa** ([@jvictordbv](https://github.com/jvictordbv)), Universidade Federal de Pernambuco (UFPE). Concepção do projeto, interface, motor híbrido (NER, LLM e PURE) e integração com o Protégé.

## Orientação acadêmica

- Prof. Dr. Fred Freitas (UFPE)
- Prof. Dr. Rinaldo Lima (UFPE)

## Coautor do software (desenvolvimento)

### Gustavo Souto Silva de Barros Santos

**Vínculo:**
- Aluno regular do mestrado do Programa de Pós-Graduação em Engenharia da Computação (PPGEC) da Universidade de Pernambuco (UPE), área de concentração Modelagem Computacional, sob orientação da Profa. Dra. Maria Lencastre.
- Aluno especial no Centro de Informática (CIn) da Universidade Federal de Pernambuco (UFPE).

**Contatos:**
- E-mail: gustavo.soutosbs@upe.br (UPE) e gssbs@cin.ufpe.br (CIn/UFPE)
- GitHub: [@gustavosouto](https://github.com/gustavosouto)
- ORCID: [0009-0004-9329-4956](https://orcid.org/0009-0004-9329-4956)
- Lattes: <http://lattes.cnpq.br/9062662189503685>
- LinkedIn: [soutogustavo](https://www.linkedin.com/in/soutogustavo)

**Contribuições** (reestruturação do projeto, a partir do PR #1):
- instalação reprodutível com uv, testes automatizados, lint e CI;
- correções da validação com o HermiT (Java), da abertura no Protégé e do IRI das ontologias;
- reorganização no pacote modular `omaker/`, com configuração central;
- geração em segundo plano, com cancelamento, e gravação dos sinônimos como `owl:equivalentClass`;
- alinhamento com ontologias externas (Symptom Ontology) sem hierarquia paralela;
- infraestrutura de treino e avaliação do classificador de relações: divisão fixa, métricas com intervalo de confiança e avaliação de ponta a ponta contra baselines;
- retirada das sobras do Gemini; treino com o BioRED; treino e avaliação retomáveis após uma queda;
- documentação: README, guia de contribuição e citação.

## Contribuições

Para ser incluído nesta lista, abra um pull request (ver [CONTRIBUTING.md](CONTRIBUTING.md)) e acrescente uma linha nesta seção, com o seu nome, o seu usuário do GitHub e um resumo da contribuição.
