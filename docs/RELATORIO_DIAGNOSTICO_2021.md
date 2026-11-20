# Diagnóstico fundamentado no ZIP enviado

Foram conferidas as imagens e as seções `TEXTO SEM ORDENAR` dos PDFs oficiais incluídas no pacote do usuário. Todos os sete enunciados existem nas fontes, com as cinco alternativas A-E. Os blocos das páginas de duas colunas foram agrupados na ordem vertical do extrator original, antecipando o cabeçalho da coluna direita e produzindo um registro vazio na coluna esquerda.

| Curso | Número | Página PDF | Enunciado recuperável | Alternativas textuais |
|---|---:|---:|---|---:|
| Ciência da Computação – Bacharelado | 9 | 19 | Sim | 5 |
| Ciência da Computação – Licenciatura | 9 | 18 | Sim | 5 |
| Ciência da Computação – Licenciatura | 26 | 33 | Sim | 5 |
| Ciência da Computação – Licenciatura | 29 | 35 | Sim | 5 |
| Ciência da Computação – Licenciatura | 31 | 36 | Sim | 5 |
| Sistemas de Informação – Bacharelado | 11 | 19 | Sim | 5 |
| Sistemas de Informação – Bacharelado | 13 | 20 | Sim | 5 |

## O que foi testado no ambiente de preparação

- Sete trechos textuais reais do diagnóstico: recuperação estrutural bem-sucedida, cinco alternativas por questão.
- Cinco testes unitários do novo parser: aprovados.
- Simulação de leitura, backup, correção de sete de 200 registros, preservação dos outros 193 e reexecução idempotente: aprovada.

**O PDF original não foi incluído no ZIP recebido**: a validação dos hashes reais dos três PDFs e o preflight com os 280 registros precisam ocorrer na máquina do usuário, onde estão os PDFs e dados originais.

O conteúdo recuperado não foi certificado por revisor humano. Os registros permanecem com `pendente_revisao=true` e alerta de revisão. Nenhuma validação semântica ou de gabarito foi inferida.
