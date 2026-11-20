$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
Write-Host 'A4 - Retomando o consumo das mensagens ja publicadas; sem reenviar dados'
py -m pytest -q .\tests\test_extracao_a3.py .\tests\test_integracao_a4.py .\tests\test_consumer_a4.py
if ($LASTEXITCODE -ne 0) { throw 'Falha nos testes automatizados' }
py .\scripts\pipeline_a4.py consumir --limite 10
if ($LASTEXITCODE -ne 0) { throw 'Falha na leitura ou indexacao' }
py .\scripts\pipeline_a4.py verificar --minimo 1
if ($LASTEXITCODE -ne 0) { throw 'Nenhum documento foi indexado. A4 ainda pendente.' }
Write-Host 'A4: registros encontrados no Elasticsearch. Salve a evidencia.'
