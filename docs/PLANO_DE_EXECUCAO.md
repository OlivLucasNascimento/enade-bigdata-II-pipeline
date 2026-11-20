# Plano de execução — duas metades sequenciais

**Referência:** PDF do enunciado, páginas 1 a 7. **Data de planejamento:** 15/11/2026. **Estado:** planejado; tarefas não executadas.

## Princípio de divisão
Cada integrante realiza a sua parte integralmente, do início ao fim, incluindo documentação e testes. O Integrante 2 só começa depois de concluído, revisado e transferido o trabalho do Integrante 1. As metades são por **blocos lógicos da arquitetura**, e não por carga horária rigorosamente igual.

## Cronograma compacto, sem paralelismo
| Data-alvo | Dono | Marco | Situação |
|---|---|---|---|
| 15–16/11 | Integrante 1 | Arquitetura, repositório, coleta-piloto, Docker Compose e definição do esquema | ☐ Pendente |
| 17–19/11 | Integrante 1 | Extração, segmentação, metadados, Kafka e consumidor Elastic | ☐ Pendente |
| 20–21/11 | Integrante 1 | Falhas, idempotência, DLQ, base de Kerberos, teste de ≥50 questões e handoff | ☐ Pendente |
| 22–24/11 | Integrante 2 | Busca Elastic, filtros, agregações, API, Redis e sessões | ☐ Pendente |
| 25–26/11 | Integrante 2 | Web React, LDAP, perfis, acesso negado 403, integração de segurança | ☐ Pendente |
| 27–28/11 | Integrante 2 | Testes, carga, métricas, revisão geral, relatório SBC e gravação do vídeo | ☐ Pendente |
| 29/11, antes de 23:59 | Responsável pela submissão | Submissão dos 3 entregáveis | ☐ Pendente |

> As datas são **metas propostas**, não prazos intermediários definidos pelo docente. O enunciado tem divergência entre prazo de entrega em 29/11/2026 e vencimento do AVA em 06/12/2026; usar a data anterior.

## Etapa 1 — Integrante 1: infraestrutura, acervo e indexação

### A1. Preparação do Git e arquitetura
- Criar repositório e branch `feat/etapa-1-pipeline` a partir de `main`.
- Documentar arquitetura e justificar quantidade de brokers, partições, shards e réplicas; registrar limites de RAM.
- Criar Docker Compose inicial para Kafka, Elasticsearch, Redis (para integração posterior), KDC Kerberos e LDAP (provisionados para a próxima etapa); cada contêiner com volumes, health checks e configuração externa segura.
- Definir `.gitignore`, `.env.example`, README de operação e portas.
- Registrar comandos, outputs e capturas em `docs/DIARIO_DE_BORDO.md`.

**Aceite:** serviços mínimos inicializados ou falhas de provisionamento registradas com causa/solução; `docker compose config` válido; arquitetura e topologia justificadas.

### A2. Inventário e coleta do acervo
- Mapear as páginas oficiais das edições, cursos, provas, gabaritos e diretrizes disponíveis do ENADE.
- Criar manifesto/CSV dos arquivos: ano, curso, categoria, tipo, URL, status, hash SHA-256 e caminho.
- Implementar download com retries, controle de taxa, checksum e logs; preservar PDFs originais em volume/diretório separado.
- **Primeiro validar com um piloto de PDFs diferentes** (com e sem diagrama, prova FG/CE, objetiva/discursiva, anulada) e depois tentar cobrir todo o acervo exigido.
- Não apresentar o piloto como coleta completa: medir cobertura real e declarar lacunas.

**Aceite:** manifesto reproduzível, URLs e hashes registrados; total de PDFs encontrados/baixados/falhos registrado.

### A3. Engenharia de dados dos PDFs
- Extrair texto, blocos, páginas e figuras sem adulterar a fonte.
- Dividir a prova em documentos de questão com enunciado, alternativas, tipo, gabarito (quando aplicável), anulada e origem.
- Tratar fórmula/diagrama/tabela com LaTeX, Mermaid ou Markdown quando possível; preservar imagem ou marcar `pendente_revisao` quando a conversão não é confiável.
- Enriquecer área, curso, ano, FG ou CE, objetos de conhecimento e competências; diferenciar extração literal de classificação inferida.
- Criar IDs determinísticos e verificar pelo menos **50 questões** por amostragem manual; registrar acertos/erros por atributo e tratamento de questões problemáticas.
- Se houver IA generativa: registrar nome do modelo, custo estimado, taxa de erro e como a amostra foi validada.

**Aceite:** JSON válido segundo o contrato e planilha/tabela de validação de 50+ questões, sem métricas inventadas.

### A4. Kafka → Elasticsearch
- Criar tópico principal `enade.questoes` e tópico de erro `enade.dlq`, com partições, políticas e retenção justificadas.
- Implementar produtor que envia eventos estruturados com chave `id` estável; produtor só confirma quando Kafka aceitar a mensagem.
- Implementar consumidor que valida esquema, realiza `upsert` no Elasticsearch com `_id` determinístico e confirma offset só depois da indexação bem-sucedida.
- Em mensagens inválidas, publicar na DLQ com motivo e contexto; tratar falhas temporárias com retry controlado.
- Criar *mapping* de campos e analyzer em português brasileiro adequado à etapa de busca.
- Configurar e registrar a estratégia inicial de Kerberos/KDC para os clientes Kafka (`SASL/GSSAPI`), além do encaminhamento seguro até o Elasticsearch; validar a licença/solução para autenticação Kerberos do Elasticsearch.

**Aceite:** uma questão real entra no Kafka e aparece no Elasticsearch; reprocessar a mesma questão não aumenta o número de documentos; mensagens inválidas vão à DLQ.

### A5. Resiliência, evidências e entrega ao colega
- Testar parada e reinício do consumidor, offsets, persistência e ausência de perda no cenário testado; registrar escopo da simulação.
- Testar logs, health checks, contagem de documentos, rastreabilidade ao PDF e métricas de docs/s e lag Kafka.
- Salvar amostras JSON, print da consulta Elastic, evidências de DLQ e relatório preliminar de qualidade.
- Revisar código, integrar `feat/etapa-1-pipeline` em `main` e registrar commit/tag de passagem `etapa-1-entregue`.
- Entregar ao Integrante 2 o documento `CONTRATO_DE_INTEGRACAO.md` atualizado e a lista das pendências reais.

**Critério de passagem obrigatório:** demonstrar os testes T01–T09 do plano de testes ou registrar claramente as falhas remanescentes; não chamar de concluído o que não foi aprovado.

## Etapa 2 — Integrante 2: aplicação, segurança final, avaliação e submissão

### B1. Recebimento
- Clonar a versão aprovada, reproduzir ambiente e executar os testes de aceite da etapa A.
- Criar branch `feat/etapa-2-aplicacao` a partir de `main`; registrar a tag/commit recebidos.
- Não alterar o contrato de eventos sem documentar migração e compatibilidade.

### B2. Consultas Elastic e API FastAPI
- Expor busca paginada, com realce de termos, filtros combináveis (área, curso, ano, tipo, competência) e estratégia de relevância PT-BR; testar interdisciplinaridade.
- Criar agregações por curso/competência/ano, histórico e endpoints `health`.
- Documentar OpenAPI/Swagger, status HTTP e mensagens de erro.
- Evitar mostrar gabaritos a Estudante em endpoints não autorizados.

### B3. Redis, sessões, carrinho e exportação
- Cache de buscas frequentes (chave inclui filtros, paginação e perfil); TTL e política de invalidação.
- Persistência temporária da seleção do usuário em Redis durante a sessão.
- Exportação de lista selecionada em JSON/PDF para Professor, conforme regra de acesso.
- Medir hit rate e comparar latência sem cache e com cache.

### B4. Interface web
- Construir login, busca, filtros, paginação, highlight, visualização de fórmulas/diagramas e lista de questões.
- Exibir recursos condicionados ao perfil: Estudante com acesso restrito a gabaritos; Professor com gabaritos, análises e exportação.
- Garantir responsividade e mensagens de erros claros.

### B5. LDAP e Kerberos
- Implementar autenticação de usuários usando servidor LDAP, mapeamento de papéis e sessão segura no backend.
- Mostrar teste em vídeo de usuário Estudante recebendo **HTTP 403** ao tentar endpoint restrito.
- Completar e comprovar autenticação mútua Kerberos entre serviços conforme topologia combinada e suporte/licença da instalação; não confundir autenticação LDAP do usuário final com Kerberos entre serviços.
- Certificar que keytabs, segredos e passwords não aparecem no Git ou nas evidências.

### B6. Testes, avaliação, relatório e vídeo
- Executar testes de carga/latência p50/p95/p99 com e sem Redis, docs/s, lag Kafka, hit rate, observabilidade e resistência a falhas.
- Gerar gráficos com títulos, eixos e unidades e discutir resultados no texto.
- Reunir métricas/evidências produzidas pelo Integrante 1 e escrever relatório SBC com **12 seções**, até **12 páginas**.
- Gravar vídeo de **até 5 minutos** exibindo fluxo de ponta a ponta, busca interdisciplinar, cache e perfis.
- Revisar README, docker compose, `.env.example` e reprodutibilidade; abrir/mesclar PR e registrar commit final.

**Aceite final:** checklist de submissão preenchido e todos os entregáveis acessíveis e testáveis.

## Topologia a justificar (proposta, não decisão final)
- Kafka: desenvolvimento com 1 broker em volume persistente, múltiplas partições; essa configuração **não é alta disponibilidade** do broker. Se houver recursos e tempo, criar 3 brokers e justificar fator de replicação/acks.
- Elasticsearch: preferir 2 nós com réplica, caso exista memória suficiente; se usar 1 nó e 0 réplica, declarar limites de tolerância à falha.
- Redis: 1 instância para cache e sessões; documentar impacto de reinício/TTL.
- KDC e LDAP: instâncias de laboratório, credenciais externas ao Git, privilégios mínimos.

**Atenção:** exigência de Kerberos no Elasticsearch pode envolver recursos/licenças não disponíveis gratuitamente; validar antes de prometer conformidade. Uma autenticação simulada não atende ao requisito.

## Regras para não perder nota
1. Cada requisito precisa ter decisão arquitetural, justificativa, evidência **e discussão**, não só print.
2. Manter histórico de comandos e capturas por etapa; jamais inventar métrica.
3. Repositório com código executável: apenas relatório/vídeo vale zero segundo o enunciado.
4. Preservar rastreabilidade ao PDF e página da questão.
5. Mesmo com dois integrantes, ambos devem compreender o sistema: o professor pode solicitar arguição oral individual.
