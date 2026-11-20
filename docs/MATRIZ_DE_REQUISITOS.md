# Matriz de requisitos e responsáveis

**Fonte:** itens 03 e 04 do PDF, páginas 2 a 4. **Legenda:** I1 = Integrante 1; I2 = Integrante 2. Todos os estados iniciais: ☐ Pendente. A documentação de segurança tem responsabilidade compartilhada, mas as mudanças de código acontecem sequencialmente.

| ID | Requisito resumido fiel ao enunciado | Dono | Evidência/teste esperado | Estado |
|---|---|---|---|---|
| RF01 | Coletar provas, gabaritos e diretrizes de cursos/edições disponíveis | I1 | Manifesto de URLs, contagem e cobertura | ☐ |
| RF02 | Uma questão por documento com enunciado, alternativas e gabarito | I1 | JSON de questão objetiva/discursiva | ☐ |
| RF03 | Diferenciar discursiva/objetiva e sinalizar anulada | I1 | Amostras dos 3 casos | ☐ |
| RF04 | Converter fórmulas, diagramas e tabelas para LaTeX/Mermaid/Markdown quando possível | I1 | Casos antes/depois e limites documentados | ☐ |
| RF05 | Área, curso, ano, FG/CE, objetos e competências | I1 | Validação de campos do esquema | ☐ |
| RF06 | Rastrear documento ao PDF e página | I1 | URL + página + checksum | ☐ |
| RF07 | Publicação em tópico Kafka por produtor | I1 | Log do produtor + leitura tópico | ☐ |
| RF08 | Consumidor indexa no Elasticsearch | I1 | Consulta de `_id` indexado | ☐ |
| RF09 | Falha de serviço sem perda de dados e retomada | I1 | Teste induzido de recuperação | ☐ |
| RF10 | Reprocessamento sem documentos duplicados | I1 | Contagem antes/depois | ☐ |
| RF11 | Mensagens inválidas encaminhadas à DLQ | I1 | Tópico de erro com motivo | ☐ |
| RF12 | Filtros combinados por área, curso, ano, tipo, competência | I2 | API e UI combinando filtros | ☐ |
| RF13 | Full-text PT-BR com stemming, sinônimos e relevância | I2 | Consultas e ranking comentado | ☐ |
| RF14 | Interdisciplinaridade entre cursos | I2 | Mesmo termo retorna cursos diversos | ☐ |
| RF15 | Histograma de competência no tempo e distribuição por curso | I2 | Agregações Elastic e gráficos | ☐ |
| RF16 | Paginação e highlight | I2 | Página 1/2 e termo destacado | ☐ |
| RF17 | API REST padronizada e Swagger/OpenAPI | I2 | `/docs` e status HTTP corretos | ☐ |
| RF18 | Cache Redis com TTL e invalidação | I2 | Hit/miss/TTL antes e depois | ☐ |
| RF19 | Lista/carrinho mantida no Redis durante sessão | I2 | Seleção recuperada após navegação | ☐ |
| RF20 | Web com busca/filtro/renders de mídia/lista | I2 | Fluxo filmado na UI | ☐ |
| RF21 | Exportação de lista para PDF ou JSON | I2 | Exportação verificada | ☐ |
| RF22 | Kerberos entre Kafka, Elasticsearch e serviços | I1: provisão; I2: integração e teste | Keytabs seguros, autenticação real e evidência | ☐ |
| RF23 | Login integrado a LDAP | I2 | Usuário LDAP real de teste | ☐ |
| RF24 | Estudante x Professor com direitos distintos | I2 | Comparação de perfis | ☐ |
| RF25 | Negar acesso indevido de Estudante com 403 no vídeo | I2 | HTTP 403 demonstrado | ☐ |

## Não funcionais
| ID | Requisito / referência | Dono da medição | Evidência necessária | Estado |
|---|---|---|---|---|
| RNF01 | p95 sem cache <500ms; com cache <50ms (referências, não obrigatoriedade absoluta) | I2 | Carga com p50/p95/p99 e cenário descrito | ☐ |
| RNF02 | Vazão da ingestão | I1 | docs/s, acervo total e duração | ☐ |
| RNF03 | Qualidade da extração | I1 | Amostra manual ≥50 questões e taxa medida | ☐ |
| RNF04 | Resiliência: zero perda após falha induzida | I1 | Experimento, mensagens pré/pós e limitações | ☐ |
| RNF05 | Escalabilidade | I1 e I2 | Justificativa de partições, shards e réplicas | ☐ |
| RNF06 | Observabilidade | I1 e I2 | Health, logs, métricas e prints | ☐ |
| RNF07 | Reprodutibilidade | I2 | README executável com `docker compose up` | ☐ |
| RNF08 | Segurança no Git | I1 e I2 | `.gitignore`, `.env.example`, scan de segredos | ☐ |

## Critério de avaliação da rubric
Os pesos totais do relatório (7,0 pontos): Arquitetura/Ingestão 1,75; Engenharia de Dados 1,00; Modelagem Elasticsearch 1,25; Cache/API/Cliente 0,75; Segurança 0,75; Avaliação Experimental 0,75; Clareza/Comunicação 0,75.

**Não marcar nenhum requisito como concluído sem evidência reproduzível.**
