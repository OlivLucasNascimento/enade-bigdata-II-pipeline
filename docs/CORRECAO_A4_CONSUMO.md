# A4 — Correção do consumidor Kafka (18/11/2026)

## Incidente e evidência

No primeiro teste real, os contêineres estavam saudáveis, 19 testes unitários passaram e 10 mensagens foram publicadas com ACK em `enade.questoes`, distribuídas pelas partições 0, 1 e 2. O consumidor respondeu `válidos=0, DLQ=0`, e o índice `enade-questoes-v1` permaneceu com 0 documentos. **A4 não estava concluída.**

## Hipótese técnica e alteração

O consumidor anterior utilizava iteração com `consumer_timeout_ms=4000`, o que pode encerrar a leitura antes da atribuição das partições durante a inscrição no grupo. A alteração substitui a iteração por `poll()` com espera de até 30 s para atribuição, log de partições/posições/finais, 15 s de inatividade após a atribuição e limites de consumo. O fluxo segue confirmando offsets somente após indexação ou publicação ACK da DLQ. É uma hipótese a confirmar na execução real, não um diagnóstico garantido.

## Como retomar sem duplicar mensagens Kafka

No PowerShell, na raiz do projeto:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\retomar-a4.ps1
```

Esse script NÃO executa o produtor: consome os eventos já publicados, verifica a presença de pelo menos um documento no índice e falha em caso contrário. Os documentos usam `_id` determinístico. `0` registros é **falha**, não sucesso.

Para verificar todos os IDs de teste e se houve 10 documentos distintos, usar:

```powershell
py .\scripts\pipeline_a4.py contar
```

Para auditar offsets do tópico independentemente:

```powershell
docker compose exec -T kafka /opt/kafka/bin/kafka-get-offsets.sh --bootstrap-server kafka:9092 --topic enade.questoes
```

## Limitações

Não houve teste local real com o Kafka do aluno na geração deste patch. Validar no Windows. O ambiente ainda é um laboratório sem Kerberos; extração de 80 questões é rascunho sujeito a revisão humana. Não usar `docker compose down -v`.
