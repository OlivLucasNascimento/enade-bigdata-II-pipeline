# Big Data II — Fechamento da Parte A (RF01–RF11)

## O que foi comprovado até agora
- A1: Kafka, Elasticsearch e Redis *healthy* no Windows.
- A2: 126 links oficiais de 2023 catalogados; somente 12 PDFs baixados; 3 reutilizados no piloto.
- A3: 80 questões de 2 provas, 80 IDs, 24 questões com referência visual, 38 imagens de páginas; 2 alternativas gráficas sem transcrição. `questoes_com_midias.jsonl` tem status editorial pendente.
- A4: 10 mensagens consumidas e indexadas no índice v1, demonstração de laboratório antes da correção editorial.
- A5: teste local de idempotência (3), DLQ (1), reinício do broker (2) registrados. Parada do consumidor sob falha de ES continua pendente.

## Para avançar rapidamente

**1) Copie o ZIP para a raiz do projeto** onde estão `compose.yaml`, `scripts`, `data`, `evidencias` e `enade_pipeline`; substitua os arquivos correspondentes sem apagar dados. O pacote adiciona principalmente arquivos novos.

**2) Revisor lado a lado, com salvamento automático por questão:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\abrir-revisao-a3.ps1
```

Abra `http://127.0.0.1:8765` no navegador. Uma questão e sua página oficial aparecem lado a lado. Avalie enunciado, alternativas e tipo com `1`/`0` e observações; ao clicar **Salvar avaliação**, o programa salva **no CSV original** `evidencias/A3_revisao_manual.csv` (com backup no começo de cada sessão). **Não marque como conferido sem observar o PDF.** Nas discursivas o critério alternativas não se aplica. Para alternativas em figuras (Arquitetura 11 e 16), se não houver representação semântica estruturada, registre `0` em alternativas e note que a página PNG existe.

**3) Verificação sem modificar dados:**

```powershell
py .\scripts\reindexar_v2.py diagnostico
```

O resultado mostra quantas avaliações estão completas. Antes das 50 avaliações a etapa seguinte será bloqueada. **Não preencha 50 avaliações com `1` sem examinar; `0` é um resultado legítimo.**

**4) Depois de revisar as 50, indexação v2 via Kafka → Elasticsearch:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\reindexar-v2.ps1
```

- Publica em um tópico Kafka **novo**: `enade.questoes.v2`; usa um grupo novo: `enade-indexador-v2`.
- Cria um índice Elasticsearch **novo**: `enade-questoes-v2` (não apaga o v1).
- Mantém os 80 IDs e identifica cada registro como `aprovada`, `reprovada`, `nao_revisada`, `em_revisao`. A amostra de 50 **não valida automaticamente os 30 restantes**.
- Indexa documentos como **rascunhos auditáveis** onde ainda existirem pendências. A contagem de 80 não é sinônimo de 80 questões corretas.
- Evidência de indexação: `evidencias/A4_v2_verificacao.json`.
- **Não confundir com segurança:** ambiente local usa Kafka PLAINTEXT e Elasticsearch HTTP, RF22 Kerberos continua pendente.

## Requisitos ainda sem demonstração integral

| Requisito | Pendência |
|---|---|
| RF01 | Não basta catalogar 126 links; obter efetivamente provas, gabaritos e diretrizes de todas as edições/cursos disponíveis, com hashes |
| RF04 | Páginas renderizadas preservam os diagramas, mas não equivalem a fórmulas LaTeX, tabelas Markdown ou diagramas Mermaid exigidos |
| RF05 | `competencias` e `objetos_conhecimento` ainda não possuem classificação verificada via diretrizes oficiais |
| RF09 | Retomada após falha *do consumidor* ou indisponibilidade do Elasticsearch sem confirmar offsets pendente |
| RF22 | Integração Kerberos SASL/GSSAPI pendente; não atribuir como concluída |
| RNFs | Latência p50/p95 com e sem cache, vazão, precisão aferida em 50, recuperação sob falhas, escalabilidade, observabilidade, reprodutibilidade e segurança devem ser medidos e registrados |
| Entrega | Relatório até 12 páginas, vídeo até 5 minutos, repositório com Docker Compose/README, declaração do uso de IA, conforme enunciado |

## Cuidados
- Nunca use `docker compose down -v`. Não compartilhe `.env` real, senhas, keytabs ou PDFs grandes no GitHub.
- O ambiente é um único broker e nó Elastic: não comprova alta disponibilidade de produção.
- O bloqueio de 50 revisões é proposital para evitar declarar dados aprovados sem conferência. O valor `0` indica falha real da extração e deve constar do relatório.
