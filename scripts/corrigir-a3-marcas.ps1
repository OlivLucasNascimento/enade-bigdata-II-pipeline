$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
Write-Host 'A3 - Auditoria e higienizacao controlada de marca VALIDINEP2023'
$backup = Join-Path 'evidencias' ('backup_A3_' + (Get-Date -Format 'yyyyMMdd_HHmmss'))
New-Item -ItemType Directory -Path $backup -Force | Out-Null
foreach ($arq in @('data/extraidos/questoes.jsonl', 'data/extraidos/pendencias.jsonl', 'evidencias/A3_revisao_manual.csv', 'evidencias/A3_resumo.json')) {
    if (Test-Path $arq) { Copy-Item $arq $backup }
}
Write-Host "Backups anteriores preservados em: $backup"
py -m pytest -q .\tests\test_extracao_a3.py .\tests\test_integracao_a4.py .\tests\test_consumer_a4.py .\tests\test_higienizacao_a3.py
if ($LASTEXITCODE -ne 0) { throw 'Testes falharam; nenhum arquivo de dados sera reextraido.' }
py .\scripts\diagnosticar_marca_pdf.py
if ($LASTEXITCODE -ne 0) { throw 'Falha na auditoria dos PDFs' }
py .\scripts\extrair_questoes.py --limite-provas 2 | Tee-Object -FilePath .\evidencias\A3_higienizacao_saida.txt
if ($LASTEXITCODE -ne 0) { throw 'Reextracao falhou' }
py .\scripts\auditar_higienizacao_a3.py
if ($LASTEXITCODE -ne 0) { throw 'Auditoria identificou dados inconsistentes' }
py .\scripts\gerar_revisao_a3.py --amostra 50
if ($LASTEXITCODE -ne 0) { throw 'Falha ao gerar amostra de revisao humana' }
Write-Host 'A3: higienizacao tecnica concluida. Revisao humana ainda obrigatoria.'
Write-Host 'Nao republicar ainda: o indice v1 tem 10 documentos de teste anteriores a esta correcao.'
