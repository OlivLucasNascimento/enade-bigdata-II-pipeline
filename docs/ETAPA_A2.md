# Etapa A2 — Coleta rastreável do acervo oficial do ENADE

**Integrante 1 (Lucas). Status: implementação preparada, ainda não executada no computador do aluno.**

## Objetivo
Descobrir e baixar provas, gabaritos e padrões de resposta disponibilizados nas páginas de **Provas e Gabaritos do INEP**, preservando proveniência (página origem, URL, ano), hash SHA-256, tamanho, data UTC e status. Atende **parcialmente RF01** (coleta), fornece insumos para **RF05** (metadados) e **RF06** (rastreabilidade). O requisito integral exige outras edições/cursos e diretrizes, que são ampliados depois; segmentação e extração são A3.

## Fonte oficial
- https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos
- Exemplo de página anual: https://www.gov.br/inep/pt-br/areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos/2023

## Como instalar/rodar (Windows PowerShell, raiz do repositório)
```powershell
py --version
powershell -ExecutionPolicy Bypass -File .\scripts\etapa-a2.ps1
```
Ou passo a passo:
```powershell
py -m pip install -r .\requirements-ingestao.txt
py -m pytest -q .\tests\test_coletar_enade.py
py .\scripts\coletar_enade.py --anos 2023 --somente-catalogo
py .\scripts\coletar_enade.py --anos 2023 --limite 3
```
Para ampliar **somente após validar os 3 PDFs e o metadado curso**:
```powershell
py .\scripts\coletar_enade.py --anos 2023,2022,2021 --limite 30
```
Para toda a lista catalogável nesses anos, usar `--limite 0` (atenção ao consumo de disco/rede). Reexecutar o mesmo comando reaproveita PDFs já válidos por assinatura e nome determinístico; compara hash e metadados em manifesto. Cada execução gera manifestos referentes ao conjunto de anos selecionado: evite mudar anos sem preservar uma cópia do manifesto anterior.

## Saídas
- `data/raw/<ano>/*.pdf`: originais (ignorados pelo Git).
- `data/manifests/catalogo_enade.csv`: tabela de descobertos, baixados, falhas, fontes, hashes.
- `data/manifests/catalogo_enade.jsonl`: mesmo catálogo em JSON Lines.

**Atenção:** um item com status `catalogado` apenas foi encontrado, não baixado. O curso é extraído de cabeçalhos da página; se não houver correspondência segura, será `nao_identificado` e deverá ser revisado manualmente. PDFs não são considerados questões extraídas. PDFs digitalizados podem exigir OCR na etapa A3. O script limita a 45 MB por PDF, valida assinatura `%PDF-` e só baixa de domínios `.gov.br`. Se o INEP alterar a estrutura do portal, a extração de metadados precisa de revisão.

## Testes exigidos e evidências para o diário
1. `py -m pytest -q .\tests\test_coletar_enade.py`: testes locais (sem acessar rede) para descoberta, deduplicação, URLs oficiais e idempotência de downloads.
2. `py .\scripts\coletar_enade.py --anos 2023 --somente-catalogo`: número efetivamente descoberto.
3. `py .\scripts\coletar_enade.py --anos 2023 --limite 3`: PDFs efetivamente baixados e hashes gerados.
4. Abrir 2 PDFs baixados manualmente, conferir curso/ano/tipo, anotar correção de metadados se necessária.
5. Testar segunda execução, confirmar status `existente` e mesmo hash.
6. Guardar saída de terminal e snapshot do manifesto, anotando data, número total, falhas e quantidade de cursos sem identificação.

## Limites / critérios pendentes
- RF01 integral: todas as edições/cursos e diretrizes; a lista de anos disponível pode mudar e nem toda edição está na mesma página.
- RF02–RF06: extração e validação de questões/metadados em A3.
- RF07–RF11: produtor/consumidor Kafka, DLQ, idempotência e retomada em A4/A5.
- RF22: integração Kerberos real, não implementada neste coletor.

## Registro-modelo (preencher APÓS executar)
- Data e horário:
- Comando:
- Resultado (números reais):
- Arquivos e hashes auditados:
- Testes:
- Erros e correções:
- Observações de qualidade (metadado curso e tipo):
- Commit:
