# RF04 — Estruturação das oito questões com elementos visuais (rascunho técnico)

## O que foi feito

A partir dos PDFs oficiais do ENADE 2023 (Agronomia e Arquitetura e Urbanismo) e das imagens PNG já validadas, foram redigidas oito representações com linhas/colunas identificadas. Os valores transcritos das questões de vacinação (Q3), mobilidade (Q5), nutrientes (Q26), germinação (Q31) e captação de água (Q32) agora possuem tabelas legíveis; os desenhos técnicos (Arquitetura Q11 e Q17) e o esquema de acústica (Q29) mantêm as imagens e incluem rótulos/associações textuais auxiliares.

**Ponto fundamental:** isto é um **rascunho de transcrição técnica assistida**, não uma nova auditoria humana. Cada tabela e descrição deve ser comparada ao PDF por um avaliador antes de se alterar qualquer status de aprovação. Não inferimos qual é o gabarito correto, nem declaramos interpretação completa dos desenhos técnicos ou equivalência acessível perfeita das imagens.

## Execução segura

```powershell
# Dentro do clone GitHub na branch de trabalho
$dados = Join-Path $env:USERPROFILE "OneDrive\Área de Trabalho\ENADE BigData II Projeto"
py .\scripts\estruturar_semantica_rf04.py --base $dados
Start-Process (Join-Path $dados "data\visuais_rf04\semantica.html")
```

Entrada: `data/extraidos_auditados_2023/questoes_visuais.jsonl`, com 80 IDs e referências PNG válidas, e `evidencias/A3_revisao_manual.csv`, contendo 50 notas originais. Apenas oito enunciados avaliados com `0` são enriquecidos com `semantica_rf04`. O script valida hashes SHA-256 dos arquivos locais, correspondência por curso, número e prefixo do ID, e preserva o texto original, alternativas, gabaritos e os outros 72 registros.

Saída: `data/extraidos_auditados_2023/questoes_semantica_rf04.jsonl`, `data/visuais_rf04/semantica.html` e `evidencias/A3_rf04_semantica_rascunho.json` **somente no projeto local**. Nenhum PDF, CSV de auditoria, Kafka ou índice Elasticsearch é modificado. O catálogo JSON com as oito transcrições e o script/testes podem ser versionados no GitHub, mas os dados brutos e imagens permanecem fora do repositório.

## Verificação humana necessária

Rever especialmente as 35 porcentagens do gráfico de vacinação, cada célula da tabela de nutrientes e as correspondências entre legenda/ícone e valores. Conferir as imagens de alternativas da Q11 uma a uma e as duas páginas da Q17. Só após a aprovação manual documentada em evidência separada será possível atualizar as notas de qualidade **do derivado**, sem modificar retroativamente o CSV histórico.

**Não reindexar o índice v3 agora.** Os 280 documentos em v3 foram publicados como rascunho e permanecem intactos. Segurança Kerberos/LDAP e validação editorial das provas de 2017/2021 continuam pendentes em frentes próprias.
