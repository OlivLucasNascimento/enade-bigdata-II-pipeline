# Diário de bordo — documentação obrigatória de cada etapa

> Registros com resultados observados são diferenciados de testes ainda pendentes. Copiar o modelo preenchível a cada sessão de trabalho; não substituir resultados reais por estimativas.

## Registro 000 — 15/11/2026 — Planejamento
- **Responsável:** Equipe (atribuir nomes posteriormente)
- **Objetivo:** leitura do enunciado e criação da divisão sequencial.
- **Fonte:** `trabalho de big data 2 - base de informações.pdf`, páginas 1–7.
- **Decisões:** primeira metade ingestão/indexação; segunda metade API/web/segurança/avaliação; prazo interno 29/11/2026.
- **Arquivos gerados nesta etapa:** conjunto de planejamento e documentação inicial em `README.md` e `docs/`.
- **Comandos executados no projeto:** nenhum.
- **Testes de software realizados:** nenhum.
- **Evidências reais de funcionamento:** nenhuma ainda.
- **Pendências:** iniciar repositório e infraestrutura; confirmar data divergente com professor; validar licença/arquitetura Kerberos do Elasticsearch.
- **Status:** Planejamento concluído; implementação NÃO iniciada.

---

## Registro 001 — 16/11/2026 — Infraestrutura A1, primeira execução
- **Responsável:** Integrante 1 (Lucas)
- **Objetivo:** iniciar a infraestrutura Kafka, Elasticsearch e Redis; criar tópicos.
- **Comandos executados:** `docker version`; `docker compose config --quiet`; `powershell -ExecutionPolicy Bypass -File .\scripts\iniciar.ps1`.
- **Resultado observado na saída informada:** Docker Client + Server disponíveis; Compose validado; três contêineres com status `Healthy` (`kafka`, `elasticsearch`, `redis`); imagens baixadas e volumes criados.
- **Falha observada:** durante `init-topicos`, `kafka-topics.sh` exibiu a ajuda de linha de comando e `iniciar.ps1` encerrou com `Falha na criacao dos topicos`.
- **Causa identificada na revisão dos arquivos:** o `command` do serviço era uma string multilinha, que o Compose interpreta como lista de argumentos e faz o Bash executar `kafka-topics.sh` sem as opções esperadas.
- **Correção proposta (não testada no computador do aluno):** converter `command` em lista YAML contendo um único script multilinha; adicionar verificação de existência de ambos os tópicos no `verificar.ps1`.
- **Evidência real:** saída de terminal recebida em conversa; ainda precisa ser salva em `evidencias/` no repositório.
- **Pendente:** executar `docker compose config --quiet`, reiniciar script, comprovar os tópicos e rodar script de evidências; depois fazer commit.
- **Status:** Em andamento — correção de configuração preparada, aguardando validação no Docker do aluno.

---

## Copiar este modelo para cada ação (001, 002, 003...)

### Registro XXX — DD/MM/AAAA HH:MM — Título
- **Integrante:** I1 ou I2 / nome:
- **Objetivo e requisito atendido:** RFxx / RNFxx:
- **Decisão técnica + justificativa:**
- **Estado inicial e pré-requisitos:**
- **Branch e commit de partida:**
- **Comandos executados (PowerShell/WSL/bash):**
  ```powershell
  # Colar aqui o comando REAL executado
  ```
- **Arquivos criados/alterados:**
- **Resultado observado e saída relevante:**
- **Testes executados (nome/comando/resultado):**
- **Métrica real (unidade, método, amostra), se houver:**
- **Evidências (caminho/print/log):** `evidencias/REG-XXX-...`
- **Discussão: por que funcionou, limites e alternativas:**
- **Dificuldades/erros e correções:**
- **Segredos ocultados nas evidências?:** Sim/Não/Não se aplica
- **Commit final + URL do PR (quando houver):**
- **Pendências para o próximo registro:**
- **Status:** Não iniciado / Em andamento / Testado / Bloqueado

### Regra de evidência
Cada print/log precisa indicar **o que está provando**, a data/ambiente e o teste correspondente. Capturas de telas sem explicação no relatório não contam como evidência válida segundo o enunciado. Nunca registrar senhas, tokens, `.env` real, chave privada ou `.keytab` em Git ou prints.
