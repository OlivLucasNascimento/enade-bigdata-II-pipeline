# ENADE Big Data II — Indexação final da representação RF04 (v4)

## Escopo e limites

A nova edição `enade-questoes-v4` e o tópico Kafka `enade.questoes.v4` são **cópias versionadas**, sem remoção, sobrescrita ou alteração de `enade-questoes-v1`, `enade-questoes-v2` e `enade-questoes-v3`. A rotina verifica os 280 documentos integralmente, além de comparar contagem e SHA-256 canônico dos documentos existentes nos índices antigos antes/depois.

As 280 questões permanecem **rascunhos técnicos no nível global**. Somente o campo `semantica_rf04` das oito questões (5 Agronomia, 3 Arquitetura) recebe o estado `APROVADA_EM_NOVA_CONFERENCIA_HUMANA`. O registro da nova aprovação é separado do CSV histórico (`evidencias/A3_revisao_manual.csv`), que continua refletindo o resultado 40/50 original. As duas discursivas 2023 têm o cabeçalho e linhas do rascunho removidos somente na versão derivada.

A declaração explícita do revisor é "8 questões conferidas e aprovadas". A evidência nova aponta para o hash do JSONL aprovado, do CSV original e do catálogo estruturado. Trocas posteriores nos arquivos invalidam automaticamente a evidência para preflight/indexação.

## Dados utilizados

O script obtém dados **somente da pasta local do projeto original**, preservando os arquivos brutos e as imagens:

- `data/extraidos/questoes_com_midias.jsonl` (80, origem original)
- `data/extraidos_auditados_2023/questoes.jsonl` (80, com 2 rascunhos limpos)
- `data/extraidos_auditados_2023/questoes_semantica_rf04.jsonl` (80, com 8 representações)
- `data/extraidos_2017_2021_corrigidos/questoes.jsonl` (200)
- `evidencias/A3_revisao_manual.csv` (50 notas históricas)
- `docs/RF04_TRANSCRICOES_ESTRUTURADAS.json` (8 descrições e tabelas)
- 14 arquivos de imagem, cujos hashes SHA-256 são verificados novamente

## Como executar (PowerShell na raiz do clone)

```powershell
$dados = Join-Path $env:USERPROFILE 'OneDrive\Área de Trabalho\ENADE BigData II Projeto'
py .\scripts\indexar_v4_rf04.py registrar-aprovacao --origem $dados --declaracao '8 questões conferidas e aprovadas'
py .\scripts\indexar_v4_rf04.py preflight --origem $dados
# Verifique o resumo antes de alterar os serviços.
docker compose up -d --wait kafka elasticsearch redis
py .\scripts\indexar_v4_rf04.py executar --origem $dados
py .\scripts\indexar_v4_rf04.py verificar --origem $dados
```

Durante `executar`, são criados (se ainda não existirem) o tópico Kafka `enade.questoes.v4`, sua DLQ `enade.questoes.v4.dlq` e o índice ES `enade-questoes-v4`. O produtor usa ACK; o consumidor usa commit manual **após** indexação ou ACK de DLQ (reutiliza `process_message` da v3). Confronta o conteúdo completo de cada documento por ID com sua origem. Se já houver documentos v4 com conteúdo inesperado, aborta sem sobrescrever; execuções repetidas com os mesmos 280 documentos são idempotentes.

## Evidências geradas

- `evidencias/A3_rf04_aprovacao_editorial_8.json` — **no clone Git**, vinculada a fontes por SHA-256;
- `evidencias/A4_v4_preflight.json` e `evidencias/A4_v4_verificacao.json` — **no clone Git**;
- `data/extraidos_280_v4/questoes.jsonl` — **somente na pasta local**, não fazer commit do arquivo bruto.

## Limitações de entrega

- A presença de referências de imagens no documento do Elasticsearch **não publica os PNGs**. A interface futura deve ler o campo `_source.semantica_rf04` e providenciar acesso aos arquivos de imagem por meio autorizado e apropriado.
- A API existente não muda automaticamente do índice v3 para o v4. O responsável pela integração deve realizar essa migração separadamente, se prevista no escopo.
- Os gabaritos, a revisão editorial integral do acervo 2017/2021, a análise semântica de todo o corpus e Kerberos/LDAP não são aprovados por esta etapa.
- A execução usa laboratório local (Kafka PLAINTEXT e Elasticsearch sem autenticação). **Não expor os serviços publicamente.**
- Nunca apagar os índices existentes para resolver erro. Interrompa e examine a saída dos comandos.
