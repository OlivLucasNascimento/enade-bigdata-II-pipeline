# A3 — Evidências visuais para questões com desenhos e imagens

## Problema
Os PDFs oficiais de 2023 contêm elementos vetoriais não retornados por `page.get_images()` (exemplos: Arquitetura e Urbanismo, questões 11 e 16). Ler somente texto deixa alternativas A–E incompletas. Não é correto inventar a descrição textual das figuras.

## Solução complementar (sem sobrescrever dados)

```powershell
py .\scripts\registrar_midias_a3.py
```

O comando usa `pymupdf` já instalado, localiza os PDFs originais pela soma SHA-256 da questão e renderiza em PNG as páginas de questões que já continham referências visuais ou que possuem alternativas exclusivamente gráficas.

- Preserva `data/extraidos/questoes.jsonl`.
- Produz `data/extraidos/questoes_com_midias.jsonl` **para revisão**, incluindo caminhos relativos em `midias`.
- Gera `data/midias/a3_paginas/*.png` e `evidencias/A3_paginas_visuais_resumo.json`.
- **Não** publica mensagens no Kafka, altera gabaritos, supõe alternativas ausentes ou marca questões como aprovadas.

O próximo integrante precisará disponibilizar `data/midias/a3_paginas/` por rota estática autenticada/autorizada ao construir a interface. Um caminho no JSONL **não é** automaticamente uma URL pública.

## Critério de conclusão
Revisar os desenhos e alternativas no PDF, avaliar 50 questões na planilha e registrar as limitações do RF04 (extração semântica de tabelas, fórmulas e diagramas ainda não resolvida). Só então criar índice Elasticsearch versionado para conteúdos aprovados e manter o v1 de testes separado.
