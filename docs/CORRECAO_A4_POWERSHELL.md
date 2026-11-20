# Correcao de sintaxe no Windows PowerShell (A4)

## Registro do incidente
- Etapa: A4, inicio da integracao Kafka e Elasticsearch.
- Sintoma: ParserError em `scripts/etapa-a4.ps1`, indicando `MissingPropertyName` na linha do caminho JSONL e fechamento incorreto de string no final.
- Diagnostico: o arquivo original estava em UTF-8 sem BOM e tinha caracteres nao ASCII (travessao e seta) em uma mensagem `Write-Host`. O Windows PowerShell 5.1 pode interpretar esses bytes com uma pagina de codigo diferente, ocasionando falha de analise sintatica.
- Correcao: mensagem substituida por texto ASCII; comandos de publicacao, consumo e indexacao preservados.
- Verificacao do artefato: o arquivo corrigido contem apenas caracteres ASCII.
- Evidencia de execucao no Windows: pendente; registrar a saida do script apos substituir.

## Procedimento
1. Extrair o ZIP de correcao na pasta do projeto (onde estao `compose.yaml` e `scripts/`), mesclando e substituindo apenas o arquivo homonimo.
2. Executar: `powershell -ExecutionPolicy Bypass -File .\scripts\etapa-a4.ps1`.
3. Conferir retorno dos testes, publicacao e consumo de 10 mensagens e contagem do Elasticsearch.

## Observacao
A integracao local continua sem Kerberos e ainda nao comprova requisitos de seguranca nem resiliência.
