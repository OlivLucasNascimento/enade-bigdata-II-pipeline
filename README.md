# ENADE Big Data II — Pipeline de coleta e ingestão

Projeto acadêmico de **coleta rastreável de documentos públicos do ENADE**, extração estruturada de questões e ingestão **Kafka → Elasticsearch**, com Redis disponível no ambiente de laboratório.

> **Estado:** protótipo técnico em andamento. A aprovação editorial humana, a cobertura integral do acervo e a autenticação Kerberos **não estão concluídas**. A configuração Docker é **somente para uso local**, sem autenticação de produção.

## Estrutura

| Pasta ou arquivo | Função |
|---|---|
| `scripts/` | Coleta oficial, extração, validação, publicação, consumo e testes de recuperação |
| `enade_pipeline/` | Funções de extração, higiene, gabaritos e integração |
| `tests/` | Testes automatizados |
| `docs/` | Arquitetura, matriz de requisitos, limitações e registros técnicos |
| `evidencias/` | Resultados verificáveis das execuções locais (sem PDFs brutos) |
| `compose.yaml` | Kafka, Elasticsearch e Redis em laboratório local |
| `requirements-ingestao.txt` e `requirements-pipeline.txt` | Dependências Python |
| `.env.example` | Modelo de configuração, sem segredos |

**Não são versionados:** PDFs oficiais, `data/`, arquivos `.env`, volumes Docker, keytabs e caches. O repositório contém código e evidências, mas o fluxo de extração real requer que os PDFs sejam coletados localmente.

## Execução local (Windows / PowerShell)

Requisitos: Python 3.12, Docker Desktop e PowerShell. Instale as dependências listadas nos dois arquivos `requirements-*.txt` e ative o Docker Desktop antes de iniciar os serviços.

```powershell
# Iniciar serviços do laboratório
docker compose up -d

# Testes automatizados
py -m pytest -q

# Catalogar links oficiais, sem baixar PDFs
py .\scripts\coletar_enade.py --anos 2017,2021,2023 --somente-catalogo
```

Para baixar **somente os documentos prioritários** do experimento (Ciência da Computação em 2017/2021 e Sistemas de Informação em 2021):

```powershell
py .\scripts\coletar_enade.py --anos 2017,2021 --cursos "Ciência da Computação,Sistemas de Informação" --tipos prova,gabarito,padrao_resposta --somente-pendentes --sem-acessibilidade --limite 15 --pausa 1
```

Os scripts abaixo dependem dos manifestos e PDFs já gerados no ambiente local (não estão presentes em um clone limpo):

```powershell
# Conferir o lote de 2017/2021, sem substituir os dados anteriores
py .\scripts\validar_correcao_2017.py

# Validar e indexar o lote de 2023 em modo rascunho
powershell -ExecutionPolicy Bypass -File .\scripts\validar-e-reindexar-v2.ps1 -Rascunho
```

Para os passos detalhados e as restrições do laboratório, consulte `docs/` e a **matriz de requisitos** em `docs/MATRIZ_DE_REQUISITOS.md`. A inicialização do Kafka e de tópicos auxiliares depende do cenário; use os scripts documentados em `scripts/`.

## Resultados de execução registrados (20/11/2026)

| Etapa | Resultado observado |
|---|---|
| A1 | Kafka, Elasticsearch e Redis saudáveis no Docker local |
| A2 | **348 links** catalogados (2017: 132; 2021: 90; 2023: 126); **33 PDFs** disponíveis; 0 cursos não identificados no catálogo |
| A3 — 2023 | **80 questões** extraídas; imagens e elementos gráficos exigem conferência editorial |
| A3 — 2017/2021 | **200 questões** no lote corrigido das cinco provas; 20 recuperadas em relação ao lote anterior; 70 itens de gabarito de 2017 vinculados |
| A4 | **80 documentos de 2023** em `enade-questoes-v2`, sem IDs faltantes ou divergência de conteúdo, **status rascunho** |
| A5 | Retomada do consumidor após falha entre indexação e commit Kafka; sem duplicação no teste isolado |
| Testes | **57 passed, 1 warning** no PowerShell, após a correção de 2017 |

**Atenção:** existem **280 registros extraídos** nos dois lotes (80 + 200), mas **somente 80 foram indexados** na v2. Contagens não comprovam, por si só, completude semântica ou correção dos enunciados/gabaritos.

## Limitações e pendências

- **Revisão humana:** amostra de 50 questões e representações visuais ainda precisam de aprovação real, registrada e rastreável. Auditoria assistida por IA não equivale à revisão humana.
- **Mídias:** algumas alternativas são exclusivamente gráficas (incluindo a questão 9 das provas de 2017); recortes PNG preservam desenhos, mas não garantem conversão para LaTeX, Mermaid ou Markdown.
- **Cobertura:** os 348 documentos estão catalogados, **não integralmente baixados**; provas, gabaritos e diretrizes de todo o acervo não estão totalmente validados.
- **Segurança:** laboratório local usa Kafka PLAINTEXT e Elasticsearch sem autenticação; **Kerberos/SASL e LDAP não foram implementados ou testados nesse ambiente**. Não disponibilize esses serviços na internet.
- **Integração do outro integrante:** API de pesquisa, filtros, Redis de aplicação, interface, exportação e controle de acesso precisam ser integrados e validados conforme a divisão de responsabilidades.

## Integridade e evidências

Os manifestos locais registram URLs oficiais, arquivos, SHA-256 e status dos downloads. A validação do lote corrigido está em `evidencias/A3_validacao_correcao_2017.json`, a confirmação da v2 em `evidencias/A4_v2_verificacao.json` e a retomada do consumidor em `evidencias/A5_rf09_retomada_consumidor.json`. Consulte `docs/STATUS_ENTREGA_A1_A5.md` e a matriz para critérios pendentes.

Este repositório não inclui os PDFs públicos originais. Consulte os links catalogados a partir da [página oficial de provas e gabaritos do INEP](https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos).
