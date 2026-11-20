# Auditoria de 50 questões — relatório e primeiro ajuste conservador

**Escopo:** 50 registros de 2023 (Agronomia e Arquitetura e Urbanismo), conferidos por pessoa usando a ferramenta local, com comparação aos PDFs oficiais. Os dados de 2017/2021 não compõem esta amostra.

**Taxas observadas:** enunciado 40/50 (80%); alternativas 48/48 aplicáveis (100%, porque duas são discursivas); tipo 50/50 (100%). Dez enunciados tiveram avaliação 0; dois casos têm rascunho numerado agregado ao texto e oito envolvem representação de elementos visuais (tabelas, gráficos, diagramas, plantas). Todos os 50 registros mantêm IDs distintos.

A rotina `consolidar_auditoria_a3.py` lê o CSV assinado pela revisão humana, valida a completude e produz um relatório JSON ligado ao hash SHA-256 do CSV. Opcionalmente remove apenas a cauda de RASCUNHO numerada das duas discursivas identificadas, gravando JSONL **derivado** e preservando íntegros CSV/JSONL brutos. Não altera os status de revisão, gabaritos, IDs, PDFs ou índices.

**Ainda pendente:** resolução semântica dos oito elementos visuais, confirmação de exibição das alternativas gráficas, conferência do lote de 2017/2021 e replicação das correções no pipeline reprodutível antes de indexar novamente. Os resultados da auditoria não devem ser alterados para indicar aprovação retroativa do extrator original.
