# Contrato inicial de integração entre integrantes (versão 0.1, sujeito a testes)

## Tópicos
- `enade.questoes`: evento JSON validado por esquema, Kafka key = ID determinístico da questão.
- `enade.dlq`: erro de validação irrecuperável, hash/referência do evento + motivo, sem interromper processamento válido.
- O consumidor deve confirmar offset só depois do sucesso no Elasticsearch **ou** da persistência confirmada na DLQ.

## Estrutura pretendida (a implementar e confirmar na A3)
```json
{
  "id": "sha256-estavel",
  "ano": 2023,
  "area": "",
  "curso": "",
  "tipo_formacao": "FG",
  "numero_questao": 1,
  "tipo_questao": "objetiva",
  "enunciado": "",
  "alternativas": [],
  "gabarito": null,
  "anulada": false,
  "competencias": [],
  "objetos_conhecimento": [],
  "midias": [],
  "pendente_revisao": true,
  "origem": {
    "pdf_url": "",
    "pdf_sha256": "",
    "pagina_inicial": 1,
    "pagina_final": 1
  }
}
```

Documentar origem dos metadados (literais, inferidos, não encontrados). Não inventar competências/gabaritos nem marcar conversão de imagem como concluída se houver apenas referência à mídia.

## Observações
- Índice proposto: `enade-questoes-v1`; campos de texto com analyzer `brazilian` e `keyword` para facetas. Mapping definitivo depende de testes.
- Protocolo definitivo entre componentes precisará adotar Kerberos (RF22); listeners PLAINTEXT do Compose atual são **somente fase A1**, não aptos à entrega final.
