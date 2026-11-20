# Fechamento incremental da parte A — ENADE Big Data II

## Escopo desta atualização (19/11/2026)

Os seguintes arquivos foram revisados sobre o `codigo_projeto_atual.zip` enviado: `registrar_midias_a3.py`, `reindexar_v2.py`, `tests/test_fechamento_a3_a4.py`, e os novos scripts/testes desta atualização. **Nenhum `compose.yaml`, PDF, volume Docker, arquivo CSV de revisão ou índice v1 é substituído.**

Os testes locais executados não utilizam Kafka/Elasticsearch de produção: a integração real ainda deve ser executada e registrada no computador Windows.

### Corrigido / protegido

1. A3: para sete questões já identificadas como relevantes visualmente (Agronomia 3, 5, 26, 31, 32; Arquitetura 11 e 29), mantém imagens das páginas originais com SHA-256 e alertas específicos no JSONL derivado. Na Arquitetura 11, remove um `N` isolado (seta de orientação da planta) apenas quando o padrão do enunciado corresponde exatamente ao caso visto no PDF. A fonte `questoes.jsonl` e PDFs não mudam.
2. O roteiro de A3 **não converte automaticamente imagens para semântica**. Tabelas Markdown, diagramas Mermaid e fórmulas LaTeX ainda exigem implementação/validação caso a caso (RF04); não relatar essa entrega como integral.
3. A4 v2: verifica **cada ID e o conteúdo**, em vez de somente `_count`; mantém tópico `enade.questoes.v2` e índice `enade-questoes-v2`, distintos do v1.
4. Revisão: observações de auditoria por IA nunca viram `revisado_humanamente=true` nem status `aprovada`; aceite humano exige confirmação explícita com hash exato do CSV. `--modo-rascunho` permite testar o pipeline sem declarar o requisito RNF03 concluído.
5. A5: acrescentado teste separado de falha após ES indexar, antes do commit Kafka. O teste usa tópico, grupo e índice de laboratório novos, preservando o projeto principal.

## Execução no Windows (uma vez, no terminal PowerShell)

- Extraia o ZIP **na raiz do projeto** (a pasta com `compose.yaml`, `scripts` e `enade_pipeline`) e escolha **substituir os arquivos no destino** quando houver. O pacote não contém `data` nem `evidencias`.
- Confirme que o Docker Desktop está em execução e que os serviços estão `healthy` com `docker compose ps`.
- **Modo rascunho para validar v2 agora, sem alegar revisão humana:**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\validar-e-reindexar-v2.ps1 -Rascunho
```

O script executa testes, audita a A3, atualiza referências visuais e faz prévia da revisão; só publica após os testes iniciais. Cria `enade-questoes-v2` e escreve `evidencias/A4_v2_verificacao.json`. Não remove o v1. Resultado esperado no piloto: 80 IDs no índice v2, todos com situação real (`nao_revisada`, `em_revisao`, `auditoria_ia` ou, se houver aceite humano válido, `aprovada/reprovada`). **Contagem de 80 não significa 80 aprovadas**.

**Se o CSV foi preenchido por IA**, mantenha o identificador de IA no campo `observacoes`. Não substitua observações nem assine confirmação sem conferir os PDFs pessoalmente.

- **Teste de recuperação real do consumidor:**

```powershell
py .\scripts\testar_rf09_retomada.py
```

A expectativa é `resultado=APROVADO`, com `offset_original` igual a `offset_reprocessado` e **1 documento antes e depois**. A evidência será `evidencias/A5_rf09_retomada_consumidor.json`. Caso falhe, registre o resultado — NÃO marque o RF09 como concluído.

- **Somente após a conferência visual humana de 50 casos:** mantenha o CSV original preenchido pela pessoa que comparou os PDFs; substitua observações de IA por observações próprias fundamentadas. Depois:

```powershell
py .\scripts\confirmar_revisao_a3.py --responsavel "NOME DO CONFERENTE"
powershell -ExecutionPolicy Bypass -File .\scripts\validar-e-reindexar-v2.ps1
```

A assinatura vincula-se ao SHA-256 do CSV. Qualquer edição posterior invalida o aceite e impede a publicação final. Se estiver sem revisão humana, use apenas o modo rascunho e registre a pendência.

## Testes e limitações da entrega

- Os arquivos fornecidos pelo aluno validaram no ambiente de análise: **80 IDs preservados**, **7 questões prioritárias com página visual** e remoção pontual do `N` na questão 11. A fonte original permaneceu inalterada.
- 37 testes relevantes (sem coleta A2) passaram no ambiente de análise. A coleta A2 utiliza `truststore`, indisponível no ambiente isolado sem rede; seus testes não foram reexecutados aqui, embora já tenham passado previamente no Windows do aluno. O script Windows executa **todos** os testes instalados.
- O pacote **não** implementa RF01 integral, preenchimento de competências por diretrizes (RF05), transcrição semântica RF04, Kerberos RF22 ou LDAP/perfis RF23–RF25. Essas exigências continuam abertas e devem constar da matriz para integração e da entrega.
- A indexação v2 integra *dados em rascunho*; não substitui a revisão humana exigida no enunciado nem valida automaticamente os gabaritos.
- O ambiente é de laboratório local com Kafka PLAINTEXT e Elasticsearch HTTP. Não publicar portas externas nem enviar keytabs/segredos ao Git.

## Registros para o diário de bordo

- **Entrada:** pacote de código do integrante 1 + PDFs ENADE 2023 e `questoes.jsonl` atual.
- **Verificações:** teste da A3 com dois PDFs; 80 IDs; 7 referências visuais prioritárias e 1 artefato de mapa removido do arquivo derivado; testes Python locais.
- **Pendências:** 50 conferências humanas, semântica gráfica/tabelas/fórmulas, acervo completo, metadados de diretrizes, integrações seguras e testes de carga/segurança.
- **Evidências:** `A3_paginas_visuais_resumo.json`, `A4_v2_verificacao.json`, `A5_rf09_retomada_consumidor.json` (estes dois últimos SOMENTE após execução local), registros de testes e commits.
