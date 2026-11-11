# Cobertura dos testes automatizados — v1.1.0

Medição de 2026-11-11 sobre a `main` da v1.1.0 (`cb4c312`), com a suíte completa e offline: modelo roteirizado, embedder de hash, Qdrant em memória e dados sintéticos, sem chamada paga nem rede.

## Método

Com o `coverage.py` 7.17.2 no ambiente de desenvolvimento, a partir da raiz do repositório:

```bash
python -m coverage run --branch --source=src/merchant_assistant -m pytest
python -m coverage report --sort=cover
```

A medição conta instruções e ramos de todos os módulos de `src/merchant_assistant`, inclusive os que nenhum teste importa.

## Resultado

| Medida | Cobertas | Total | Cobertura |
| --- | ---: | ---: | ---: |
| Instruções | 13.747 | 14.649 | **93,8%** |
| Ramos | 3.754 | 4.268 | **88,0%** |

A suíte tem 3.060 casos de teste, de 1.447 funções: 1.704 casos unitários (607 funções, 45 arquivos) e 1.356 de integração (840 funções, 57 arquivos). São 98 módulos medidos.

| Pacote | Módulos | Instruções | Instruções cobertas | Ramos cobertos |
| --- | ---: | ---: | ---: | ---: |
| `guardrails` | 3 | 121 | 100,0% | 95,2% |
| `observability` | 5 | 399 | 99,5% | 93,9% |
| `agents` | 10 | 998 | 98,5% | 96,6% |
| `data` | 6 | 258 | 98,1% | 96,8% |
| `orchestration` | 5 | 848 | 96,5% | 90,9% |
| `evaluation` | 14 | 3.927 | 96,3% | 91,6% |
| `ticketing` | 7 | 597 | 95,8% | 88,0% |
| `tools` | 4 | 543 | 94,5% | 81,9% |
| `api` | 8 | 2.299 | 93,4% | 89,4% |
| `rag` | 9 | 896 | 90,4% | 77,4% |
| módulos da raiz do pacote (CLI, comparações, conversas, encaminhamentos, perfis) | 12 | 2.665 | 90,4% | 84,3% |
| `mocks` | 4 | 164 | 90,2% | 69,2% |
| `integrations` | 2 | 459 | 89,8% | 83,1% |
| `llm` | 9 | 475 | 80,8% | 52,1% |

O cliente do provedor de modelos (`llm/openai_llm.py`) e a coleta das páginas oficiais (`rag/collect.py`) falam com serviços externos e são exercitados pelas campanhas com modelo real e pela ingestão, fora da suíte offline. Sem esses dois módulos, a cobertura de instruções é 94,5%.
