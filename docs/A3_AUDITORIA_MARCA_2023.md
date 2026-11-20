# A3 — Auditoria da marca VALIDINEP2023

## Problema observado (execução real — 18/11/2026)

- 80 registros extraídos de 2 provas de 2023 (76 objetivas, 4 discursivas).
- 72 registros continham `VALIDINEP2023` ou `VALIDIN3P2023` em algum campo JSONL.
- 10 registros de teste foram indexados em `enade-questoes-v1` antes da descoberta da contaminação. **Esse índice NÃO é um conjunto de questões validadas.**

## Correção controlada

1. Faz backup do JSONL e dos registros anteriores em `evidencias/backup_A3_*`.
2. Verifica se a marca existe também na camada textual dos arquivos PDF originais, registrando páginas e contagens em `evidencias/A3_marca_na_fonte_pdf.json`.
3. Reextrai as duas provas e preserva **`data/extraidos/questoes_brutas.jsonl`** sem alterações.
4. Cria `data/extraidos/questoes.jsonl` removendo **apenas** sequências exatas identificadas pelo padrão `VALIDIN(?:E|3)P2023`.
5. Mantém `pendente_revisao=true` e adiciona `marca_validinep_removida_revisar` aos alertas das questões afetadas.
6. Registra ID, página, SHA256 da origem, campo alterado e número de remoções em `data/extraidos/auditoria_marcas.jsonl`.
7. Compara IDs, quantidades e marcas residuais e gera `evidencias/A3_auditoria_higienizacao.json`.
8. Regenera amostra de 50 questões para revisão manual, salvando eventual CSV anterior no backup.

## Limitações e pendências

A remoção das sequências conhecidas não corrige automaticamente artefatos de OCR/extração, hifenização, figuras, fórmulas, saltos de coluna, alternativas incorretas ou questões não detectadas. **Não há aprovação automática da qualidade.** A comparação com os PDFs e a revisão humana de no mínimo 50 questões continuam obrigatórias.

`enade-questoes-v1` ainda contém 10 documentos anteriores à correção; não tratá-lo como dado limpo. Antes de disponibilizar a API ao colega, reindexar dados revisados (idealmente em um índice novo) e registrar as evidências da versão.

## Como executar

Na pasta do projeto, com Python e PyMuPDF instalados:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\corrigir-a3-marcas.ps1
```

Não executar `docker compose down -v` e não apagar PDFs, backups ou manifestos.
