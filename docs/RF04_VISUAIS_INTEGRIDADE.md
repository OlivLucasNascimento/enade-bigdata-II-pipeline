# RF04 — Oito pendências visuais da auditoria humana ENADE 2023

A auditoria manual de 50 questões encontrou dez enunciados com problemas: duas
questões discursivas com linhas de **RASCUNHO** embutidas e oito questões com
representações visuais cuja semântica não foi preservada adequadamente.

Este passo **não certifica que as oito questões foram corrigidas semanticamente**.
Reaproveita os arquivos existentes, valida seus SHA-256, associa-os a cada
questão e cria uma galeria offline para conferência. Preserva enunciados,
alternativas, IDs, status de revisão e CSV original. Nunca grava no Elasticsearch.

## Uso no Windows

Após executar os testes (`py -m pytest -q`), no repositório Git:

```powershell
$dados = Join-Path $env:USERPROFILE 'OneDrive\Área de Trabalho\ENADE BigData II Projeto'
py .\scripts\preparar_visuais_rf04.py --base $dados
if ($LASTEXITCODE -ne 0) { throw 'Falha ao validar elementos visuais' }
Start-Process (Join-Path $dados 'data\visuais_rf04\galeria.html')
```

## Saídas locais (fora do Git)

- `data/extraidos_auditados_2023/questoes_visuais.jsonl`: 80 registros, sem alterar IDs,
  com campo adicional `apresentacao_visual_rf04` nos oito casos.
- `data/visuais_rf04/galeria.html`: interface offline para visualizar os
  documentos/imagens referenciados e alternativas gráficas.
- `evidencias/A3_rf04_visuais_integridade.json`: diagnóstico e hashes dos arquivos.

O script valida existência de mídia e SHA-256 e confirma que a Questão 11 de
Arquitetura e Urbanismo possui as alternativas A–E ligadas a imagens. A questão
17 pode possuir três referências de mídia, mas apenas dois caminhos únicos;
isso não constitui, por si só, falha.

## Casos ainda sujeitos a interpretação visual (não aprovados)

| Curso | Questão | Tipo de elemento |
|---|---:|---|
| Agronomia | 3 | Gráfico de vacinação infantil |
| Agronomia | 5 | Infográfico de mobilidade |
| Agronomia | 26 | Tabela de nutrientes |
| Agronomia | 31 | Curva das fases de germinação |
| Agronomia | 32 | Gráfico de distribuição de captação de água |
| Arquitetura e Urbanismo | 11 | Planta e cinco alternativas gráficas |
| Arquitetura e Urbanismo | 17 | Plantas e fachadas |
| Arquitetura e Urbanismo | 29 | Diagrama acústico |

O RF04 pede conversão semântica para Markdown/LaTeX/Mermaid **quando possível**.
Uma página inteira renderizada como PNG é referência visual válida, mas não
substitui uma tabela Markdown ou gráfico estruturado com valores vinculados.
A etapa seguinte deverá tratar e validar semanticamente cada caso.

**Não mude as notas 0 da auditoria original.** Uma correção posterior requer
reavaliação da nova versão; a auditoria original mede a qualidade do extrator
antes das correções. Não reindexar v3 sem novo pipeline versionado e verificação.
