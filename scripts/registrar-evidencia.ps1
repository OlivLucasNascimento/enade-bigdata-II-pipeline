$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
$saida = Join-Path $PWD "evidencias\A1-servicos-$((Get-Date).ToString('yyyyMMdd-HHmmss')).txt"
"Data: $((Get-Date).ToString('yyyy-MM-dd HH:mm:ss zzz'))" | Out-File -FilePath $saida -Encoding utf8
"Docker: $(docker --version)" | Out-File -FilePath $saida -Encoding utf8 -Append
"Compose: $(docker compose version)" | Out-File -FilePath $saida -Encoding utf8 -Append
"`nContainers:" | Out-File -FilePath $saida -Encoding utf8 -Append
docker compose ps | Out-File -FilePath $saida -Encoding utf8 -Append
"`nTopicos Kafka:" | Out-File -FilePath $saida -Encoding utf8 -Append
docker compose exec -T kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:9092 --list | Out-File -FilePath $saida -Encoding utf8 -Append
"`nElastic:" | Out-File -FilePath $saida -Encoding utf8 -Append
(Invoke-RestMethod 'http://127.0.0.1:9200/_cluster/health' | Select-Object cluster_name,status,number_of_nodes | ConvertTo-Json) | Out-File -FilePath $saida -Encoding utf8 -Append
"`nRedis:" | Out-File -FilePath $saida -Encoding utf8 -Append
docker compose exec -T redis redis-cli ping | Out-File -FilePath $saida -Encoding utf8 -Append
Write-Host "Evidencia registrada em: $saida"
