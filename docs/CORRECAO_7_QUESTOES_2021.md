# Recuperação controlada de 7 questões ENADE 2021

## Causa observada

Em páginas oficiais de duas colunas, os cabeçalhos QUESTÃO N e QUESTÃO N+1 aparecem na mesma altura. A ordenação dos blocos por coordenada vertical no extrator atual faz a questão da esquerda ser encerrada antes da leitura do respectivo texto; o registro resulta com `enunciado` vazio. O diagnóstico inclui imagens e `get_text('text', sort=False)` em ordem original, que demonstra a presença dos textos e alternativas.

## Escopo e segurança

O script `scripts/corrigir_7_questoes_2021.py` recupera **somente sete IDs previamente identificados**, lê as páginas originais, valida o SHA-256 de cada PDF, compara o texto com o diagnóstico local, extrai o bloco correspondente e exige as cinco alternativas A-E antes de escrever. Verifica preservação dos outros 193 registros, 200 IDs únicos e contagem por ano, gera backup nomeado pelo hash SHA256 e relatório em `evidencias/A3_correcao_7_questoes_2021.json`.

O script é idempotente: em uma segunda execução, exige que os valores correspondam ao PDF, e não faz nova alteração. O backup fica na pasta local de dados, que não deve ser publicado no GitHub.

**Não considera as questões revisadas humanamente.** Não elimina alertas de revisão, não atribui novos gabaritos, não aplica Kerberos, não indexa nada em Kafka/Elasticsearch e não corrige questões de outros anos que possam ter misturas de colunas. Dados, PDFs e diagnóstico são locais.

## Execução

```powershell
# Na pasta enade-bigdata-II-pipeline, branch feat/indexacao-2017-2021
py -m pytest -q
py .\scripts\corrigir_7_questoes_2021.py --diagnostico
py .\scripts\corrigir_7_questoes_2021.py
py .\scripts\indexar_v3.py preflight
```

**Não execute `indexar_v3.py executar` antes de examinar o relatório do preflight.** Um preflight positivo comprova integridade estrutural do lote, não revisão editorial. A integração Kafka/ES continua etapa separada.
