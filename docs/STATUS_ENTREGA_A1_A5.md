> **Documento historico:** retrata a primeira etapa do pipeline. Para resultados finais da indexacao, consulte o README e docs/INDEXACAO_V4_RF04.md.

# Status verificável — Big Data II / ENADE (primeira parte)

## Concluído no ambiente Windows do projeto (saídas fornecidas pelo integrante)

- A1: Kafka, Elasticsearch e Redis com contêineres saudáveis.
- A2: 348 documentos oficiais catalogados (2017: 132, 2021: 90, 2023: 126); 33 arquivos PDF disponíveis no último relatório; 0 cursos não identificados no catálogo após correção de 2021. **Não equivale à coleta integral dos 348 documentos**.
- A3: lote 2023 com 80 questões; duas alternativas exclusivamente gráficas de Arquitetura com recortes associados; revisão humana pendente.
- A4: `enade-questoes-v2` com 80 documentos, IDs preservados e sem divergências no teste local, em modo **rascunho**.
- A5: retomada do consumidor após indexar e antes de confirmar offset Kafka, sem duplicação, aprovada no laboratório local.
- Testes existentes: 52 aprovados antes da correção dos PDFs de 2017.

## Correção de 2017 (inspecionada e testada em ambiente isolado)

- A extração anterior tinha 27 objetivas + 3 discursivas por prova; a correção recuperou **35 objetivas + 5 discursivas** por prova.
- As cinco provas prioritárias 2017/2021 devem fornecer 200 questões no lote corrigido (80 de 2017 + 120 de 2021).
- O pacote adiciona cinco testes novos; a suíte reconstruída passou com **57 testes** no ambiente de teste. Confirmação Windows ainda necessária.
- Reconhecimento e vínculo dos 35 gabaritos oficiais por curso de 2017 devem ser conferidos com o script `validar_correcao_2017.py` em Windows.
- O lote corrigido é mantido à parte. Não atualizar o índice Elasticsearch sem análise posterior.

## Pendências não resolvidas automaticamente

1. Revisão editorial e humana da amostra de 50 questões e dos trechos visuais, de fórmulas e de código. Não usar status “aprovado” por IA.
2. Conferir os gabaritos dos cinco cursos e o acervo não baixado; 348 catalogados ≠ 348 disponíveis.
3. Definir e implementar o ambiente de autenticação Kerberos/SASL conforme os requisitos do professor. O laboratório testado está sem Kerberos.
4. Atualizar evidências de execução real após corrigir 2017; validar requisitos e publicar PR após a conferência.

## Segurança de entrega

Não publicar arquivos `.env`, keytabs, credenciais, PDFs grandes, cache ou `data/raw`. Documentar como obter os PDFs oficiais e como gerar a extração localmente.
