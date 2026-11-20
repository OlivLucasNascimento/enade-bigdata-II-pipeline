$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
$backup = Join-Path 'evidencias' ('backup_A3_ordenacao_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach ($arq in @('data/extraidos/questoes.jsonl', 'data/extraidos/questoes_brutas.jsonl', 'data/extraidos/pendencias.jsonl', 'evidencias/A3_revisao_manual.csv', 'evidencias/A3_resumo.json')) {
    if (Test-Path $arq) { Copy-Item $arq $backup -Force }
}
Write-Host "Backup anterior em: $backup"
py -m pytest -q .\tests
if ($LASTEXITCODE -ne 0) { throw 'Testes falharam: dados anteriores preservados.' }
py .\scripts\extrair_questoes.py --limite-provas 2
if ($LASTEXITCODE -ne 0) { throw 'Reextracao falhou' }
py .\scripts\avaliar_a3_seguro.py
if ($LASTEXITCODE -ne 0) { throw 'Auditoria tecnica identificou erro.' }
py .\scripts\gerar_revisao_a3.py --amostra 50
if ($LASTEXITCODE -ne 0) { throw 'Falha na amostra de revisao.' }
Write-Host 'A3 - Atualizacao tecnica aplicada. Revise 50 questoes e figuras antes da entrega.'
Write-Host 'NAO PUBLICAR: indice Elasticsearch v1 ainda contem questoes anteriores a correcao.'
