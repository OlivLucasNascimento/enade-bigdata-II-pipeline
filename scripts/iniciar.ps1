$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host 'Validando Compose...'
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Compose invalido' }
Write-Host 'Subindo Kafka, Elasticsearch e Redis...'
docker compose up -d kafka elasticsearch redis
if ($LASTEXITCODE -ne 0) { throw 'Erro ao subir contêineres' }
Write-Host 'Aguardando servicos ficarem saudaveis (pode levar alguns minutos)...'
docker compose up --wait -d kafka elasticsearch redis
if ($LASTEXITCODE -ne 0) { throw 'Servicos nao saudaveis. Execute: docker compose ps; docker compose logs --tail 80' }
Write-Host 'Criando topicos de forma idempotente...'
docker compose run --rm init-topicos
if ($LASTEXITCODE -ne 0) { throw 'Falha na criacao dos topicos' }
Write-Host 'Executando validacoes...'
& "$PSScriptRoot\verificar.ps1"
