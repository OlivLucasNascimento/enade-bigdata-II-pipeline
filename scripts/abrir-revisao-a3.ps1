$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
Write-Host 'Revisao A3: abra http://127.0.0.1:8765 e preencha as 50 questoes.'
Write-Host 'As notas sao salvas diretamente no CSV original, com backup da sessao.'
py .\scripts\revisar_a3_web.py
if ($LASTEXITCODE -ne 0) { throw 'Falha no servidor local de revisao A3' }
