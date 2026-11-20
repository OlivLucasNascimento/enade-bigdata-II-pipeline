$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
Write-Host "`n--- CONTAINERS ---"
docker compose ps
if ($LASTEXITCODE -ne 0) { throw 'Erro ao consultar Docker' }
Write-Host "`n--- TOPICOS KAFKA ---"
$topicos = @(docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list)
if ($LASTEXITCODE -ne 0) { throw 'Kafka falhou' }
$topicos | Out-Host
foreach ($esperado in @('enade.questoes', 'enade.dlq')) {
    if ($topicos -notcontains $esperado) { throw "Topico obrigatorio nao encontrado: $esperado" }
}
Write-Host "`n--- ELASTICSEARCH ---"
$es = Invoke-RestMethod -Uri 'http://127.0.0.1:9200/_cluster/health' -TimeoutSec 15
$es | Select-Object cluster_name,status,number_of_nodes | Format-List
if ($es.status -notin @('yellow','green')) { throw 'Elasticsearch indisponivel' }
Write-Host "`n--- REDIS ---"
docker compose exec -T redis redis-cli ping
if ($LASTEXITCODE -ne 0) { throw 'Redis falhou' }
Write-Host "`nValidacao A1 concluida. Registre screenshot e hash do commit."
