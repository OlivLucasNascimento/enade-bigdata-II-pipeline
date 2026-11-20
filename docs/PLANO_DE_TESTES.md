# Plano de testes e métricas

**Status:** planejado; **nenhum teste executado**. Cada execução deve registrar data, máquina, versão, corpus, passos, saída, falha e evidência.

## Testes da Etapa 1 — Integrante 1
| ID | Cenário | Passos e resultado esperado | Evidência |
|---|---|---|---|
| T01 | Coleta de PDF | Executar crawler; manifesto lista fontes, hash e status; conferir PDF aberto | CSV, logs, arquivo |
| T02 | Segmentação | Extrair questão objetiva e discursiva; campos corretos e páginas preservadas | JSON e comparativo PDF |
| T03 | Anulação | Processar questão anulada; `anulada=true`, sem descarte | JSON e origem |
| T04 | Mídia | Processar equação/figura/tabela; marcar o que não puder converter com fidelidade | Antes/depois e alerta |
| T05 | Metadados | Conferir curso/ano/FG-CE/competências e rastreabilidade | Amostra comentada |
| T06 | Pipeline | Publicar 1+ questões Kafka e consultar Elastic por `_id` | Log produtor/consumidor/Elastic |
| T07 | Idempotência | Reprocessar mesmo PDF e comparar quantidade de `_id` únicos | Contagem antes/depois |
| T08 | DLQ | Publicar mensagem malformada; tópico de erro recebe motivo sem parar fluxo | Dump do tópico e log |
| T09 | Recuperação | Pausar consumidor; produzir N mensagens; reativar; conferir N processadas e offsets | Experimento e totalizações |
| T10 | Qualidade | Revisar **no mínimo 50** questões de anos/cursos/mídias diversos | Planilha manual e taxa medida |
| T11 | Vazão | Contar docs indexados / tempo efetivo; detalhar hardware | Docs/s e duração |

## Testes da Etapa 2 — Integrante 2
| ID | Cenário | Passos e resultado esperado | Evidência |
|---|---|---|---|
| T12 | Filtros | Buscar com área + curso + ano + tipo + competência | API e tela |
| T13 | Busca full-text | Termos em português, com variações morfológicas e sinônimos declarados | Resultados/ranking |
| T14 | Interdisciplinaridade | Buscar `ética`; encontrar questões de cursos diferentes (se presentes no acervo) | Prints com cursos distintos |
| T15 | Agregações | Ver distribuição por curso e histograma competência x ano | JSON/gráfico discutido |
| T16 | Paginação | Avançar página e conferir highlight | API/tela |
| T17 | OpenAPI | Abrir Swagger e testar status 200/400/401/403/404 conforme cenário | `/docs` e respostas |
| T18 | Cache | Mesma consulta antes e depois, demonstrar miss/hit e TTL/invalidação | Redis + latência |
| T19 | Carrinho | Criar sessão, selecionar questão, navegar, voltar e confirmar seleção | Captura da UI/Redis |
| T20 | Exportação | Professor exporta carrinho JSON/PDF; conferir conteúdo | Arquivo gerado |
| T21 | LDAP | Logar dois usuários do diretório com papéis diferentes | Logs limpos + perfil na UI |
| T22 | Permissões | Estudante acessa rota restrita via API, recebe **403**; documentar no vídeo | Requisição/resultado |
| T23 | Kerberos | Verificar comunicação autenticada GSSAPI no Kafka e solução real de acesso ao Elastic e serviços | KDC/JAAS sem segredos; logs |
| T24 | Desempenho | Carga controlada; comparar p50/p95/p99 com e sem cache | Gráfico com unidades |
| T25 | Git/Compose | Clonar do zero, configurar `.env.example` e executar procedimento documentado | Log de instalação |
| T26 | Segurança Git | Conferir ausência de tokens, passwords e keytabs versionados | Ferramenta/resultado do scan |

## Fórmulas de métricas e interpretação
- **Vazão (docs/s):** número de documentos realmente indexados dividido pelo tempo medido (em segundos).
- **Qualidade de extração (%):** acertos segundo rubrica manual / total de campos/questões avaliados × 100. Definir explicitamente a unidade do julgamento (questão integral vs campo).
- **Hit rate Redis (%):** hits / (hits + misses) × 100, no intervalo do teste.
- **Lag Kafka:** diferença de offsets disponíveis e consumidos por partição, registrar instante e método.
- **Latência p50/p95/p99 (ms):** percentis das amostras de tempo de resposta em cenários com mesmo corpus, QPS/concor­rência, aquecimento e ambiente.
- **Resiliência:** documentar tipo de falha e comparar mensagens válidas produzidas, indexadas e pendentes após recuperação.

As referências RNF01 são **p95 <500 ms sem cache e p95 <50 ms com cache**; o PDF explicita que atingir todas as metas não é estritamente obrigatório, mas **medir, registrar e explicar** é indispensável. Não alegar resultados antes de medi-los.

## Tabela para resultados reais
| Teste | Data/ambiente | Entrada/amostra | Resultado numérico/observação | Passou? | Evidência | Discussão |
|---|---|---|---|---|---|---|
| A preencher | — | — | — | — | — | — |
