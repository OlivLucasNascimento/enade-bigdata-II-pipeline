# Correção A3 — leitura do manifesto no Windows

**Falha observada no ambiente do integrante (18/11/2026):** `2 failed, 9 passed` durante `etapa-a3.ps1`. Os dois testes pararam em `RuntimeError: Nenhuma prova disponível no manifesto`.

**Diagnóstico do código:** `pdf_from_manifest` usava `str(Path(...)).startswith('data/')` para validar o prefixo dos caminhos do CSV. No Windows, `Path('data/raw/...')` é representado por `data\\raw\\...`; assim, a validação com `data/` falhava. O extrator descartava as entradas válidas do manifesto antes de tentar ler os PDFs.

**Correção:** normalizar e validar o caminho como relativo e independente do sistema operacional (`PurePosixPath`), aceitar os dois separadores usuais e bloquear caminhos absolutos, unidades Windows e travessia (`..`). Não foi necessário alterar o Docker Compose, baixar PDFs novamente ou desabilitar qualquer verificação de segurança.

**Validação realizada durante a preparação do patch:** `python -m pytest -q tests/test_extracao_a3.py tests/test_integracao_a4.py` -> **19 passed** em ambiente de desenvolvimento. Inclusos testes de regressão para `/` e `\\`, e testes para rejeição de caminhos inseguros. **A execução no Windows e a extração de provas reais ainda devem ser verificadas pelo integrante**.

**Aplicação:** extrair o ZIP na raiz do projeto, onde fica `compose.yaml`, e mesclar as pastas, substituindo `enade_pipeline/extracao.py` e `tests/test_extracao_a3.py` quando solicitado. Em seguida, executar:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\etapa-a3.ps1
```

**Evidências:** guardar saída do terminal, `evidencias/A3_resumo.json`, `evidencias/A3_saida.txt`, `data/extraidos/questoes.jsonl` e `data/extraidos/pendencias.jsonl`, quando existirem. Validar amostra manual antes de considerar qualidade da extração concluída.

**Status:** correção entregue e testada localmente; validação real pendente.
