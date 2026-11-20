# ENADE Big Data II — Etapas A3, A4 e testes iniciais A5

**Integração:** pacote incremental para mesclar à raiz do projeto que já contém `compose.yaml`, `data/raw`, `scripts/coletar_enade.py` e os PDFs do aluno.

## Antes de executar

- Docker Desktop / Kafka / Elasticsearch / Redis já foram confirmados na A1. NÃO apague volumes (`docker compose down -v`).
- O manifesto `data/manifests/catalogo_enade.csv` deve conter os 12 PDFs da A2 e seus caminhos locais.
- O pacote **não altera** o arquivo `compose.yaml` nem o coletor A2; apenas adiciona novos arquivos.
- Todos os resultados A3/A4 são novos e estão **pendentes de validação no computador do aluno**.
- Os tópicos `enade.questoes` e `enade.dlq` já existem. O índice `enade-questoes-v1` é criado na A4.

## 1. A3 — extrair 2 provas de cursos distintos

No **PowerShell**, na pasta que contém `compose.yaml`:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\etapa-a3.ps1
```

O script instala PyMuPDF, kafka-python, elasticsearch-py e pytest, executa testes e processa **no máximo duas provas regulares de cursos diferentes** já obtidas na A2. Saídas:

- `data/extraidos/questoes.jsonl`: **uma questão por linha**, com ID determinístico (SHA-256), enunciado, alternativas detectadas, ano, curso, seção FG/CE, páginas, PDF de origem e gabarito quando reconhecido.
- `data/extraidos/pendencias.jsonl`: hash incompatível, PDF escaneado, ausência de questões ou problemas de leitura.
- `evidencias/A3_resumo.json` e `evidencias/A3_saida.txt`: volume de provas, quantidade de questões, vazão, falhas detectadas.
- `evidencias/A3_revisao_manual.csv`: amostra determinística de até 50 questões para conferência manual (não contém respostas pré-preenchidas).

Para processar mais **cursos distintos** depois de revisar o piloto:

```powershell
py .\scripts\extrair_questoes.py --limite-provas 0
py .\scripts\gerar_revisao_a3.py --amostra 50
```

**Não confunda progresso com qualidade:** PDF extraído não significa que os textos foram extraídos corretamente. Conferir questões objetivas, discursivas, figuras, gabaritos e páginas com as provas originais. Não inventamos competências, objetos de conhecimento nem descrições de imagens; `pendente_revisao=true` até avaliação.

## 2. A4 — Kafka → Elasticsearch

Após A3 produzir `questoes.jsonl` não vazio:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\etapa-a4.ps1
```

Isso usa os serviços A1 e, em ordem: roda testes, cria o índice (se ausente), publica **até 10** mensagens no Kafka, consome e indexa, consulta total do índice. Execute somente em máquina com Docker ativo.

Comandos separados para evidenciar:

```powershell
py .\scripts\pipeline_a4.py criar-indice
py .\scripts\pipeline_a4.py publicar --limite 10
py .\scripts\pipeline_a4.py consumir --limite 10
py .\scripts\pipeline_a4.py contar
```

O consumidor grava no ES com `_id` determinístico; não cria um segundo documento ao reprocessar o mesmo ID. Os offsets são confirmados **somente depois** de indexar com sucesso ou de obter ACK de publicação na DLQ. Falha do Elasticsearch interrompe o processamento sem confirmar o offset não processado.

O tópico de dados tem 3 partições, a DLQ 1; replica=1 porque há um só broker. Índice ES tem 1 shard primário e 0 réplicas para permanecer saudável no único nó. Configurações são **válidas para laboratório**, não para HA/produção.

## 3. A5 — experimentos REAIS (não marcados como concluídos)

### Teste de idempotência RF10

1. Execute `py .\scripts\pipeline_a4.py contar`, guarde a contagem C1.
2. Reexecute `py .\scripts\pipeline_a4.py publicar --limite 10` e depois `py .\scripts\pipeline_a4.py consumir --limite 10`.
3. Execute `py .\scripts\pipeline_a4.py contar`, guarde a contagem C2.
4. Se todas as 10 mensagens já estavam indexadas, `C1 == C2` comprova que o mesmo ID não criou duplicatas. Guarde as saídas.

### Teste de mensagens inválidas/DLQ RF11

```powershell
py .\scripts\pipeline_a4.py enviar-invalido
py .\scripts\pipeline_a4.py consumir
# Ler até 1 mensagem da DLQ (somente ambiente de teste):
docker compose exec -T kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic enade.dlq --from-beginning --max-messages 1 --timeout-ms 10000
```

A mensagem de DLQ contém motivo, hash e localização do evento inválido. Conferir se ela foi escrita e se os eventos seguintes continuam. A mesma mensagem pode aparecer mais de uma vez em DLQ se houver falha entre ACK e commit — sem garantia de exactly-once.

### Teste de resiliência RF09/RNF04 (manual, posterior)

Com o consumidor parado, publique mensagens válidas, interrompa apenas o Elasticsearch com `docker compose stop elasticsearch`, tente consumir e observe que a operação falha **sem confirmar o offset da mensagem não indexada**. Reinicie com `docker compose start elasticsearch` e reexecute o consumidor; confira a contagem antes/depois. Registre o número de mensagens enviadas, mensagens consumidas e eventual perda. **Não** interromper o único broker e prometer alta disponibilidade: Kafka com 1 broker/1 réplica não é tolerante a perda do próprio broker.

### Qualidade de extração RNF03

Uma **amostra mínima de 50 questões** precisa ser conferida por pessoa contra os PDFs. Preencha `enunciado_correto_1_ou_0`, `alternativas_corretas_1_ou_0`, `tipo_correto_1_ou_0` e observações no arquivo CSV. Depois execute:

```powershell
py .\scripts\resumir_revisao_a3.py
```

Com menos de 50 preenchimentos, o script declara amostra insuficiente. A aferição do desempenho precisa especificar PDFs, curso/ano, condições da máquina, total de documentos e duração. `evidencias/A3_resumo.json` contém `arquivos_por_segundo` para vazão inicial RNF02 (não é a vazão Kafka).

## 4. Limitações não resolvidas por este pacote

- **RF01 integral:** baixar/acessar todas as edições e diretrizes disponíveis, além dos 12 PDFs piloto; acervo bruto pode ocupar vários GB.
- **RF02/03:** melhorar heurísticas para provas em duas colunas, tabelas e gabaritos heterogêneos; comparar manualmente resultados. Gabarito só vinculado quando reconhecido na tabela oficial, e `***` não vira letra em discursiva.
- **RF04:** conversão de fórmulas/diagramas/tabelas em LaTeX/Mermaid/Markdown **ainda não implementada**. Registro de imagens é apenas referência preliminar; revisão humana indispensável.
- **RF05:** competências/objetos de conhecimento não são inferidos sem diretrizes confiáveis, portanto estão vazios e pendentes.
- **RF22 (obrigatório):** Kerberos SASL/GSSAPI para Kafka/Elasticsearch NÃO está implementado; Compose ainda usa PLAINTEXT/HTTP local. Integrante 1 deve preparar desenho/KDC, integrante 2 finaliza integração, testes e evidências. **Não alegar RF22 atendido.**
- **A4/A5:** testes locais reais ainda devem ser executados. O índice de laboratório sem autenticação não pode ser exposto na rede.
- **RNF05:** um nó não prova escalabilidade/alta disponibilidade. Justificar limites e plano de expansão.
- **RNF07:** quando o sistema estiver completo, revisar `README` e disponibilizar execução via `docker compose up` reproduzível em máquina limpa.

## 5. Evidências para relatório

- `evidencias/A3_saida.txt` (saída do script)
- `evidencias/A3_resumo.json` (resumo da extração)
- `evidencias/A3_revisao_manual.csv` (somente após revisão humana)
- Captura do terminal com Kafka ACK (partição/offset) e consulta ao Elasticsearch.
- Print das contagens antes/depois da reindexação e conteúdo de DLQ.
- Comando Git para salvar evidências sem dados brutos: `git status` e `git log -1 --oneline` (não inventar hash).

**Segurança:** nunca envie `.env`, senhas, arquivos keytab ou PDFs grandes ao Git. Verifique `.gitignore`, dado que a pasta `evidencias` ignora alguns arquivos por padrão.
