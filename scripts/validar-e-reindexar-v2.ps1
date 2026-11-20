param([switch]$Rascunho)
$ErrorActionPreference = 'Stop'
Set-Location (Resolve-Path (Join-Path $PSScriptRoot '..'))
Write-Host 'Validando integridade antes de publicar no Kafka...'
py -m pytest -q .\tests
if ($LASTEXITCODE -ne 0) { throw 'Testes falharam' }
py .\scripts\avaliar_a3_seguro.py
if ($LASTEXITCODE -ne 0) { throw 'Auditoria da extracao falhou' }
Write-Host 'Atualizando referencias das imagens do PDF oficial...'
py .\scripts\registrar_midias_a3.py
if ($LASTEXITCODE -ne 0) { throw 'Geracao de imagens falhou' }
Write-Host 'Recortando alternativas graficas das questoes 11 e 16 (Arquitetura)...'
py .\scripts\completar_alternativas_visuais.py
if ($LASTEXITCODE -ne 0) { throw 'Associacao de alternativas graficas falhou' }
Write-Host 'Diagnostico da revisao: '
py .\scripts\reindexar_v2.py diagnostico
if ($LASTEXITCODE -ne 0) { throw 'Diagnostico falhou' }
Write-Host 'Verificando os tres servicos Docker...'
docker compose ps
if ($LASTEXITCODE -ne 0) { throw 'Docker indisponivel' }
if ($Rascunho) {
    Write-Host 'MODO RASCUNHO: documentos nao serao identificados como validados humanamente.'
    py .\scripts\reindexar_v2.py executar --modo-rascunho
} else {
    Write-Host 'MODO FINAL: exige aceite humano e CSV revisado; sem aceite, bloqueia.'
    py .\scripts\reindexar_v2.py executar
}
if ($LASTEXITCODE -ne 0) { throw 'Reindexacao v2 nao foi validada' }
Write-Host 'Indexacao v2 tecnicamente confirmada. Indice v1 mantido.'
