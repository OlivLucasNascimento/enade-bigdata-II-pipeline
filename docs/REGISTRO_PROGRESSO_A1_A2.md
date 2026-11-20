# Registro confirmado pelo terminal do integrante 1 — A1/A2

Fonte: saídas fornecidas pelo aluno na conversa. Não são medições realizadas na máquina do assistente.

## A1 — 16/11/2026

- `docker version`: Client 29.7.2 e Server Docker Desktop 4.87.0.
- `docker compose config --quiet`: validação concluída sem erros.
- `scripts/iniciar.ps1`: Kafka `healthy`, Redis `healthy`, Elasticsearch `healthy` (cluster `green`, 1 nó).
- Tópicos `enade.questoes` e `enade.dlq` criados.
- Redis `PONG`; script `registrar-evidencia.ps1` gravou arquivo A1 de evidências.
- Uma falha no comando Bash do serviço `init-topicos` foi corrigida sem apagar volumes.

## A2 — 16/11/2026

- Primeiro catálogo 2023: 126 links oficiais.
- Primeiro download de 3 provas falhou por validação SSL; correção com `truststore` preservando verificação TLS.
- Após a correção: `pytest`: **5 passed, 1 warning** (aviso de depreciação de plugin externo), 3/3 PDFs baixados, falhas 0.
- Hashes SHA-256 dos 3 arquivos calculados e enviados pelo aluno; primeira reexecução: 3 `existente`.
- Coleta com `--limite 12`: 12 arquivos processados, falhas 0, 3 cursos (Agronomia, Arquitetura e Urbanismo, Biomedicina), 9 novos e 3 existentes.
- `Get-ChildItem .\\data\\raw -Recurse -File -Filter *.pdf | Measure-Object`: 12 arquivos no disco.
- Manifesto CSV foi copiado para `evidencias/A2_catalogo_2023_12.csv`.
- **Situação:** coleta piloto validada; RF01 integral (demais edições e diretrizes) pendente.

## A3/A4/A5 — situação em 18/11/2026

Código adicional gerado e testado localmente com PDFs de teste sintéticos, não com os PDFs reais do aluno. É preciso executar `scripts/etapa-a3.ps1` e, depois, `scripts/etapa-a4.ps1` no Windows para obter resultados reais. Não registrar volumes/contagens previstos como medições.
