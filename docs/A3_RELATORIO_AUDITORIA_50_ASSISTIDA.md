# Relatório de auditoria assistida por IA — ENADE 2023

## Escopo e origem
Comparação de 50 registros amostrados em `A3_revisao_manual.csv` e presentes em `questoes(1).jsonl` com as provas oficiais fornecidas de **Agronomia** (40 páginas) e **Arquitetura e Urbanismo** (48 páginas). Conferência de campos de identificação, tipo da questão, enunciados, textos das alternativas e páginas de origem. Uso de extração textual e inspeção visual dirigida de páginas com gráficos, diagramas e tabelas.

## Resultado
| Indicador | Ocorrências |
|---|---:|
| Questões avaliadas tecnicamente | 50 |
| Textos/enunciados sem pendência essencial detectada | 43 |
| Questões com pendência essencial de enunciado/mídia | 7 |
| Alternativas textuais A–E compatíveis | 47 de 48 objetivas |
| Objetivas sem alternativas estruturadas | 1 (Arquitetura 11) |
| Classificação objetiva/discursiva compatível | 50 de 50 |
| Questões com pendência visual ou semântica | 22 |

## Questões com problemas prioritários
- Agronomia 3, p. 5: gráfico de vacinação, relação entre os dados e as séries não preservada.
- Agronomia 5, p. 7: infográfico de mobilidade sem associações visuais confiáveis.
- Agronomia 26, p. 24: tabela tabular sem estrutura de colunas/linhas.
- Agronomia 31, p. 29: curva das fases da germinação não representada como figura no JSONL.
- Agronomia 32, p. 30: gráfico de demanda de água sem representação visual estruturada.
- Arquitetura e Urbanismo 11, p. 15: desenhos A–E não transcritos, e símbolo 'N' indevidamente capturado no enunciado.
- Arquitetura e Urbanismo 29, p. 35: diagrama de transmissão acústica sem referência visual estruturada.

## Interpretação dos campos de avaliação
- `1` no enunciado: conformidade técnica de texto/estrutura identificada, sem problema essencial de mídia identificado. Não certifica correção de conteúdo científico, gabarito ou semântica de imagens.
- `0` no enunciado: ausência de representação visual essencial ou contaminação identificada.
- `1` em alternativas: 5 alternativas textuais identificadas no PDF e reproduzidas no JSONL; `0` quando a questão contém desenhos sem transcrição; vazio para discursiva.
- `1` em tipo: o cabeçalho no PDF corresponde à categoria declarada no JSONL.

## Restrições e uso acadêmico
Trata-se de **auditoria assistida por IA**, e não da revisão humana que possa ser exigida no enunciado. Os campos foram preenchidos como resultado técnico revisável; as avaliações dos 22 casos visuais não devem ser apresentadas como aprovação editorial definitiva. Os arquivos originais foram mantidos. A correção da extração/reindexação deve ser repetida após sanar as divergências. Este relatório não inclui validação independente de gabaritos, diretrizes, questões fora da amostra ou outros anos de ENADE.
