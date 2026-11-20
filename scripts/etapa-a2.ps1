$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
py --version
if ($LASTEXITCODE -ne 0) { throw 'Python nao encontrado (instale Python 3.11+ e habilite o comando py)' }
py -m pip install -r .\requirements-ingestao.txt
if ($LASTEXITCODE -ne 0) { throw 'Falha na instalacao das dependencias' }
py -m pytest -q .\tests\test_coletar_enade.py
if ($LASTEXITCODE -ne 0) { throw 'Testes do coletor falharam' }
Write-Host '\nCatalogando os PDFs oficiais do ENADE 2023...'
py .\scripts\coletar_enade.py --anos 2023 --somente-catalogo
if ($LASTEXITCODE -ne 0) { throw 'Falha ao catalogar o portal do INEP' }
Write-Host '\nBaixando os tres primeiros PDFs (teste inicial)...'
py .\scripts\coletar_enade.py --anos 2023 --limite 3
if ($LASTEXITCODE -ne 0) { throw 'Falha ao baixar PDFs. Consulte logs SSL e docs/CORRECAO_SSL_A2.md' }
Write-Host 'ETAPA A2 — teste inicial concluido. Confira os manifestos em data/manifests.'
