# Big Data II — Fechamento da Parte A (RF01–RF11)

## Situação demonstrada em ambiente local (18/11/2026)
- A1: Docker Compose, Kafka, Elasticsearch e Redis saudáveis.
- A2: 126 links oficiais de 2023 catalogados; 12 PDFs baixados. Cobertura completa RF01 ainda não demonstrada.
- A3: piloto com 2 PDFs, 80 questões. Correção adicional da ordenação testada com os dois PDFs originais: 80 IDs preservados, zero fragmentos `VALIDIN*` nos campos textuais, 2 questões de Arquitetura com alternativas predominantemente gráficas e não estruturadas. *Isto não representa aprovação da qualidade editorial.*
- A4: 10 eventos indexados em `enade-questoes-v1` antes da limpeza; índice é de teste e contém dados antigos.
- A5: idempotência (3 mensagens), DLQ (1 mensagem), broker reiniciado (2 mensagens) testados. Falta parada/retomada do consumidor com controle de offset.

## Ordem para menor retrabalho (não confundir teste-piloto com cumprimento integral)

1. **A3 / Correção de leitura** — aplicar `scripts/atualizar-a3.ps1`, guardar evidências, manter `questoes_brutas.jsonl`.
   - Confirmar 80 questões, 80 IDs, 0 marcas `VALIDIN*` e 2 questões gráficas pendentes, conforme PDFs da amostra.
   - Não inventar as alternativas gráficas nem esconder a ausência de imagens, fórmulas, tabelas e diagramas.
2. **RF04 / Conteúdo não textual e RF05 / metadados** — tratar imagens/diagramas/tabelas com referência e conversão (Markdown/Mermaid/LaTeX conforme o tipo), mantendo confirmação por pessoa; preencher objetos do conhecimento e competências a partir de matriz/diretrizes oficiais, não por inferência sem fonte. A estrutura atualmente guarda listas vazias.
3. **RNF03 / Amostra de 50** — comparar enunciados, alternativas, tipo e presença de elementos visuais com o PDF; preencher `evidencias/A3_revisao_manual.csv` com 0/1 e observações. Para discursivas, alternativas = não se aplica. Computar precisão sobre a amostra efetivamente verificada. A avaliação manual não foi executada automaticamente.
4. **A2 / RF01** — ampliar a coleta para os anos, cursos e documentos exigidos, com controle de espaço em disco, retomada, SHA-256 e manifestos por edição; reportar o que foi realmente coletado, não apenas catalogado.
5. **A4 / RF07–RF08** — após revisão, indexar em novo índice versionado, evitando misturar com `enade-questoes-v1`; validar contagem, IDs únicos, fonte/ano/curso e gabarito. O índice v1 atual é apenas de testes.
6. **A5 / RF09–RF11** — registrar experimento de parada do consumidor entre publicação e confirmação de offset; verificar retomada sem perda, idempotência e DLQ em execução real.
7. **Segurança transversal / RF22** — definir com o Integrante 2 estratégia real de Kerberos (SASL/GSSAPI), principais/keytabs e integração com Kafka, Elasticsearch e serviços; ambiente atual sem Kerberos **não satisfaz RF22**. Verificar licenciamento/compatibilidade do Elasticsearch antes de depender de recursos restritos.
8. **A6 / Entrega** — revisão de README, scripts de instalação, testes, relatório com arquitetura, decisões de tópicos/partições/shards/réplicas, gráficos de throughput, RNF01–RNF08 e evidências. Repositório sem senhas, PDFs grandes ou `.env` real. Passagem validada ao Integrante 2.

## Critérios de aceite objetivos
- RF01: manifesto e número real de provas, gabaritos e diretrizes por curso/edição, com hashes.
- RF02–RF03: extração de questões numeradas; objetivas/discursivas/ anuladas conforme fonte.
- RF04: mídias referenciadas e representadas quando aplicável, com pendências explícitas; sem perdas silenciosas.
- RF05–RF06: metadados completos e fonte PDF/página por item.
- RF07–RF08: produtor/consumidor funcionando, IDs únicos e índice com dados revisados.
- RF09: experimento de falha do consumidor e recuperação sem perda, com evidências.
- RF10: reprocessamento não cria duplicatas.
- RF11: evento malformado direcionado à DLQ com erro observável.
- RF22: integração segura demonstrada, não apenas planejada.
- RNF03: pelo menos 50 avaliações manuais e cálculo documentado da taxa de acerto.

## Importante
Os marcos descritos como "aprovados" correspondem somente ao escopo explicitamente testado. Não confundir 12 PDFs com o acervo integral, a remoção de marcas com qualidade de extração validada, nem saúde do Docker com autenticação Kerberos.
