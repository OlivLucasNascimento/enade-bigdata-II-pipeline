# Registro de execução — fechamento da Etapa A1

**Responsável:** Integrante 1 (Lucas)
**Data informada no contexto de execução:** 16/11/2026
**Origem da evidência:** saída do terminal PowerShell enviada na conversa (ainda precisa ser armazenada no repositório, sem segredos).

## Ações que foram efetivamente realizadas
- Docker Engine inicialmente inacessível; após iniciar Docker Desktop, `docker version` passou a mostrar Client e Server.
- `compose.yaml` localizado; `docker compose config --quiet` concluiu sem erro.
- Primeiro `iniciar.ps1` iniciou os contêineres, mas falhou na criação de tópicos porque o comando `init-topicos` não passou argumentos corretos ao Kafka.
- `compose.yaml` corrigido foi aplicado e `iniciar.ps1` executado novamente.

## Resultado efetivamente observado na segunda execução
- `kafka`: `Healthy`.
- `elasticsearch`: `Healthy` e cluster `green`, 1 nó.
- `redis`: `Healthy`, comando `PING` respondeu `PONG`.
- Tópicos Kafka `enade.questoes` e `enade.dlq` criados e listados.
- Script exibiu `Validacao A1 concluida. Registre screenshot e hash do commit.`

## Limites e pendências
- Trata-se de topologia de desenvolvimento com um nó Kafka e um nó Elasticsearch. Não demonstra alta disponibilidade.
- Sem Kerberos/LDAP e sem TLS: **RF22, RF23 e RF24 pendentes**, não devem ser declarados atendidos.
- Falta salvar em `evidencias/` o log gerado por `scripts/registrar-evidencia.ps1` e inserir o hash de um commit Git real.

## Discussão
O problema de `init-topicos` foi de passagem de argumentos via Docker Compose/Bash, não de indisponibilidade do broker. A correção preservou os volumes; os testes reais mostraram que os serviços e os tópicos ficaram operacionais.
