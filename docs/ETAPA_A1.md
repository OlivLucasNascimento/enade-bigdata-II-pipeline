# Registro de execução — A1 (Infraestrutura)

**Status:** três serviços observados como Healthy em 16/11/2026; criação dos tópicos falhou e correção está preparada, pendente de reexecução e evidências.

## Decisões e justificativas
1. Escolher Docker Compose para reprodutibilidade (RNF07) e reduzir configuração manual.
2. Kafka Apache 3.9.1 em KRaft com um broker para viabilizar o piloto em máquina comum; replicação 1 significa que **não há alta disponibilidade de broker**. Três partições preparam paralelização do consumidor. Tópico de erro separado para DLQ (RF11).
3. Elasticsearch 8.17.0 em single node com volume persistente; fator de réplica final será definido com base em RAM e testes (RNF05).
4. Redis 7.4 com AOF e volume, pronto para segundo integrante; login LDAP e Kerberos serão adicionados em fase própria.
5. Portas `127.0.0.1` e segredos ignorados no Git: laboratório isolado, **ainda não segurança completa** (RNF08, RF22 pendentes).

## Evidência necessária
- Data, nome da máquina (opcional), RAM e Docker/Compose version.
- Resultado real de `docker compose ps` com serviços healthy.
- Listagem dos dois tópicos e partições.
- Elasticsearch respondendo no endpoint de health.
- Redis retornando PONG.
- Discussão: por que um broker/um nó não suporta indisponibilidade total.

## Registro A1 — a preencher APÓS executar
- Data/hora:
- Responsável (Integrante 1):
- Branch/commit:
- Comandos executados:
- Resultado do Kafka:
- Resultado do Elasticsearch:
- Resultado do Redis:
- Tempo gasto:
- Erros e correções:
- Arquivo(s) de evidência:
- O que permanece pendente:

## Critério de aceite
A1 só é concluída se a execução real gerar saúde verificável de Kafka, ES e Redis, tópicos criados, arquivo de evidência e commit Git.
