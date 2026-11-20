$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
Write-Host 'Verificando infraestrutura...'
docker compose ps
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose indisponivel' }
Write-Host 'Validando 50 revisoes e preparando reindexacao versao 2...'
py .\scripts\reindexar_v2.py executar
if ($LASTEXITCODE -ne 0) { throw 'Reindexacao v2 incompleta - verifique a mensagem acima' }
Write-Host 'Versao v2 confirmada. Indice v1 foi preservado.'
