# Registro técnico — Falha de certificado SSL na Etapa A2

## Incidente observado (16/11/2026)
- Ambiente: Windows, Python 3.12.10, Requests 2.34.2.
- Descoberta de URLs: **126 links oficiais catalogados para 2023**; metadados sem curso não identificado: 0 (segundo log).
- Testes anteriores: **4 passed, 1 warning** (`anyio`/pytest; aviso não é a causa da falha).
- Downloads tentados: 3 provas de Agronomia (padrão, ledor e ampliada), **0 baixados**.
- Erro registrado: `SSLCertVerificationError: unable to get local issuer certificate`, precedido em uma tentativa por `ConnectionResetError(10054)`.
- Estado: **RF01 ainda parcial — não houve download comprovado**.

## Hipótese e correção implementada
O `requests` utiliza normalmente o conjunto de autoridades certificadoras do `certifi`, que pode não incluir raízes presentes no repositório de certificados do Windows (inclusive em redes com inspeção HTTPS por antivírus/proxy). A biblioteca `truststore` permite usar a cadeia de confiança do sistema.

Alterações:
1. `requirements-ingestao.txt`: `truststore>=0.10.4,<1`.
2. `scripts/coletar_enade.py`: injeção do truststore antes do import do requests, mantendo HTTPS com validação de certificado e nome do host.
3. `tests/test_coletar_enade.py`: verifica que `session.verify` permanece `True`.
4. `scripts/etapa-a2.ps1`: diagnóstico mais específico em falhas de download.

**Não foram usados `verify=False`, flags de SSL inseguro ou desligamento de inspeção HTTPS.**

## Passos de validação
A partir da pasta que contém `compose.yaml`:

```powershell
py -m pip install -r .\requirements-ingestao.txt
py -m pytest -q .\tests\test_coletar_enade.py
py .\scripts\coletar_enade.py --anos 2023 --limite 3
```

Verificar o número de arquivos `.pdf` válidos em `data/raw/2023`, os respectivos SHA-256 e os status `baixado` ou `existente` do manifesto `data/manifests/catalogo_enade.csv`. Testar repetição para evidenciar idempotência.

Se ainda houver erro TLS, **não desabilitar a verificação**. Verificar relógio/data do Windows, comportamento do endereço no navegador e se antivírus ou proxy está apresentando certificado não confiável no próprio Windows. Se a cadeia não for confiável no sistema, a biblioteca corretamente continuará a recusar o download. Para testes, é possível obter manualmente um PDF do site oficial e registrar sua URL e SHA-256 no manifesto.

## Evidências a preencher após teste real
- Data e horário da execução:
- Comando executado:
- Resultado dos 5 testes:
- Total de PDFs efetivamente baixados:
- URLs e SHA-256 dos documentos:
- Logs/prints guardados:
- Commit da correção:
