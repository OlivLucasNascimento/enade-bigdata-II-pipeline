# Big Data II — redução das pendências de A1–A5 (20/11/2026)

## Situação demonstrada no ambiente Windows do integrante

- A1: Kafka, Elasticsearch e Redis saudáveis no Docker local.
- A3: 80 questões extraídas de **dois PDFs oficiais de 2023** (40 Agronomia, 40 Arquitetura), não do acervo completo; extração técnica aprovada, ainda não há revisão humana das 50.
- A4: índice **enade-questoes-v2** com 80 documentos; 80 IDs conferidos, sem divergências; **status `nao_revisada`** (rascunho). Índice v1 preservado.
- A5: 42 testes automatizados aprovados antes deste pacote. Teste de recuperação RF09/RF10 em Kafka/ES aprovado: mesmo offset lido duas vezes e 1 documento antes/depois.
- Segurança: Kafka PLAINTEXT e Elasticsearch HTTP, **Kerberos NÃO configurado**. Não expor este laboratório na internet.

## O que este pacote implementa

1. **RF02/RF04 parcial:** dois itens com alternativas exclusivamente gráficas (Arquitetura 2023, Q11 p.15 e Q16 p.21) passam a ter objetos A–E **associados a 10 PNGs recortados do PDF oficial**. Cada objeto contém letra, caminho do recorte e sinalização explícita de que não existe transcrição semântica. Não se presume gabarito ou validade editorial. O JSONL original não é alterado.
2. **RF01/A2:** o coletor passa a **preservar historicamente os manifestos** ao consultar outros anos. PDFs anteriormente marcados como baixados só conservam esse status se existirem no caminho original e o SHA-256 conferir. Gera CSV/JSONL de maneira temporária/atômica. Não há coleta de rede nesta entrega.
3. Testes unitários de mapeamento dos recortes e acúmulo do manifesto.
4. Auditoria assistida das 50 questões arquivada SEPARADAMENTE em `evidencias/A3_auditoria_assistida_IA.csv`, sem sobrescrever `A3_revisao_manual.csv`.

## Aplicação (somente no projeto ORIGINAL que contém `data/raw` e PDFs)

Extraia o ZIP na raiz `ENADE BigData II Projeto`, substituindo `scripts/validar-e-reindexar-v2.ps1` e `scripts/coletar_enade.py`. Preserve as pastas `data` e os CSVs originais. Rode:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validar-e-reindexar-v2.ps1 -Rascunho
```

Esse comando executa os testes, regenera imagens e as 10 alternativas recortadas, e reindexa a v2. A v1 não é apagada. Verifique:

- `evidencias/A3_alternativas_graficas_recortadas.json` = 10 recortes, 2 questões.
- `evidencias/A4_v2_verificacao.json` = 80 IDs, 0 faltantes, 0 divergentes.
- `data/midias/alternativas_graficas/` = os 10 PNGs para a futura interface web.

### Ampliar catálogo sem baixar PDFs

```powershell
py .\scripts\coletar_enade.py --anos 2017,2021,2023 --somente-catalogo
```

**Atenção:** isso catalogará apenas os links encontrados nas páginas de anos indicados, não fará download nem extração das novas questões. O próximo passo de coleta deve ser planejado com quota de disco/rede e verificação das fontes. O script tem limite de 45 MB por PDF e default de apenas 3 downloads, portanto NÃO presume a coleta integral. Em caso de erro de rede, registre a evidência.

## Pendências que NÃO podem ser declaradas concluídas

| Requisito | Pendência | Depende de |
|---|---|---|
| RNF03 | Revisão **humana** de 50 questões, incluindo conteúdo gráfico e gabaritos; a auditoria por IA não equivale à revisão humana | Integrante revisor humano, comparando com PDFs oficiais |
| RF01/RF05/RF06 | Cobertura real de cursos/edições, coleta de gabaritos/diretrizes e ligação validada de competências, objetos, área, origem e páginas | Coleta ampliada e validação editorial das diretrizes |
| RF04 | Tradução semântica de gráficos/tabelas/fórmulas para Markdown/LaTeX/Mermaid **quando viável**, com validação | Revisão caso a caso (recorte PNG não equivale à conversão) |
| RF22 | Autenticação Kerberos real com KDC, principals/keytabs seguros e configuração de clientes/serviços | Configuração conjunta de infraestrutura e Integrante 2 |
| RF23–RF25 | LDAP, perfis Estudante/Professor e 403 | Integrante 2 |
| RNF02/05/06 | Medição de ingestão, estratégia de escalabilidade e observabilidade | Experimentos e evidências adicionais |

## Envio ao GitHub

Após testar no projeto original, copie os novos arquivos de `scripts/`, `tests/`, `docs/` e `evidencias/A3_auditoria_assistida_IA.csv` para a cópia Git **sem `data/`, PDFs, keytabs, `.env` ou volumes Docker**. Não usar `git add -f` para forçar arquivos ignorados. Antes do commit: `git status --short`, `git diff --cached --stat`, `py -m pytest -q`. Não declare revisão humana nem Kerberos como concluídos.
