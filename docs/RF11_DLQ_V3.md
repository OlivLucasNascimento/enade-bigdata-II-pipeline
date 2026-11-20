# RF11 — Dead Letter Queue (DLQ) para o consumidor ENADE v3

## O que mudou

- O consumidor de `enade.questoes.v3` agora usa a DLQ dedicada `enade.questoes.v3.dlq`.
- Quando JSON/UTF-8, esquema da questão ou status de rascunho são inválidos, o consumidor publica na DLQ: **motivo**, SHA-256, conteúdo original em Base64, data UTC e tópico/partição/offset originais.
- O offset da mensagem inválida **só é confirmado após receber ACK do Kafka na DLQ**.
- A mensagem válida só recebe commit após a chamada de indexação bem-sucedida no Elasticsearch.
- Se o Elasticsearch ou a publicação na DLQ falhar, o erro é propagado e **não ocorre commit antecipado**. Em uma reentrega, podem existir registros repetidos na DLQ; não foi implementado exactly-once.
- O comando `configurar-dlq` cria somente a DLQ, **não envia novamente as 280 questões** e não grava em Elasticsearch.

## Teste com Docker (Windows PowerShell)

Na raiz do repositório e em uma branch de feature:

```powershell
docker compose up -d --wait kafka elasticsearch redis
py -m pytest -q
py .\scripts\indexar_v3.py configurar-dlq
py .\scripts\testar_rf11_v3.py
```

`testar_rf11_v3.py` cria **tópicos e índice de teste isolados**. Envia um JSON inválido, um JSON com esquema incompleto e um documento sintético válido; os dois inválidos precisam aparecer na DLQ com payload, motivo e offsets, e o válido deve aparecer no índice isolado. Compara a contagem dos índices v1/v2/v3 antes e depois. Não escreve nos tópicos/índices de dados oficiais. Não apaga índices ou volumes após o teste.

**Evidência** após execução real aprovada: `evidencias/A5_rf11_v3_dlq.json` (`resultado: APROVADO`). Os testes unitários não substituem esse experimento Kafka/Elasticsearch real.

**Limitações:** laboratório `PLAINTEXT` sem Kerberos; não expor portas a redes externas. A DLQ não oferece exatamente-uma-vez e requer política de retenção e reprocessamento para ambiente produtivo.
