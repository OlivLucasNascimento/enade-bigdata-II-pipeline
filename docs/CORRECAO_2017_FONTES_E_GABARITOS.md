# ENADE 2017 — correção de fonte, colunas e gabaritos

## Problema reproduzido

Os dois PDFs oficiais de Ciência da Computação de 2017 contêm caracteres com mapeamento Unicode não convencional. A representação gráfica é legível, mas a extração textual convencional mostrava, por exemplo, `Yh\x1c^d\x08K\x03Ϭϰ` em lugar de **QUESTÃO 04**. Por isso oito cabeçalhos objetivos não eram encontrados em cada prova. Algumas páginas apresentam duas colunas independentes e as tabelas de gabarito de 2017 usam **ITEM / GABARITO**, em vez do padrão de 2023.

## Correção realizada

- Decodificação de índices de glifos obtidos das fontes incorporadas aos dois PDFs oficiais, com ativação limitada aos hashes SHA-256 dessas provas. Não inclui nem distribui arquivos de fontes.
- Ordem de leitura por coluna em páginas com cabeçalhos nos dois lados, sem alterar o algoritmo das provas de 2023.
- Reconhecimento de alternativas A–E com texto iniciado em letra minúscula.
- Reconhecimento conservador de tabela 2017 de 35 respostas; qualquer número ausente ou conflito impede a associação parcial.
- Questão 9 de cada prova mantém referência ao PDF para as cinco alternativas gráficas, **sem fingir que são alternativas transcritas**.

## Verificações locais realizadas

- Em cada PDF de 2017: **35 objetivas e 5 discursivas**; 34 objetivas com cinco alternativas em texto e Q9 com cinco alternativas gráficas.
- Todos os 30 IDs previamente extraídos por prova foram preservados na nova extração (60/60).
- Extração dos dois PDFs de 2023 permaneceu com 40 questões por caderno.
- As questões e fontes precisam de revisão editorial. A decodificação não garante correção semântica de gráficos, trechos de código, fórmulas e tabelas.

## Execução no ambiente do projeto

```powershell
py -m pytest -q
py .\scripts\validar_correcao_2017.py
```

O script gera `data/extraidos_2017_2021_corrigidos/`, **sem substituir** `data/extraidos_2017_2021/` e sem publicar no Kafka. Exige que as cinco provas e os gabaritos oficiais estejam acessíveis no manifesto prioritário. O diagnóstico fica em `evidencias/A3_validacao_correcao_2017.json`.

Se houver falhas de contagem, gabarito ou IDs, NÃO integrar nem indexar os registros resultantes.
