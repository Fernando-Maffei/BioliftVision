# Estrutura do Projeto (Atualizada)

Este guia descreve a organização atual do projeto após a reestruturação para eficiência e clareza.

## Visão em alto nível
- `app/`: inicializadores e wrappers da aplicação.
- `common/`: utilitários compartilhados (logger, paths, helpers de player).
- `core/`: lógica de negócio e análise (keypoints, ângulos, scoring, treino, inferência).
- `config/`: configurações e requisitos.
- `dataset/`: dados brutos e processados.
- `db/`: acesso a banco, repositórios e testes de conexão.
- `docs/`: documentação (fluxos, guias, este arquivo).
- `logs/`: saídas de execução e auditoria.
- `model/`: modelos treinados e manifesto.
- `results_oneclass/`: artefatos de avaliação.
- `storage/`: persistência local (preferência do usuário, avaliações, etc.).
- `ui/`: interface PyQt5 e componentes.

## Destaques da UI
- `ui/style.py`: paleta e constantes de tema (`PRIMARY_COLOR`, `SURFACE_COLOR`, `TEXT_COLOR`, etc.).
- `ui/chips.py`: criação e layout de chips de status.
  - `make_chip(status)`: chip estilizado para `valid`, `invalid`, `pending`.
  - `update_chips_grid(parent, grid, chips, available_width)`: organiza chips em 1–2 linhas.
- `ui/responsive.py`: utilitários de responsividade.
  - `compute_right_panel_width(window_width)`: breakpoints para o painel direito.
  - `clamp_left_width(max_left_width, desired_width)`: evita invasão visual da área direita.
- `ui/interface.py`: tela principal; agora usa `chips` e `responsive`.

## Fluxo do core
- `core/train_model.py`: treinamento (OneClass) e otimização simplificada.
- `core/run_model.py`: inferência e avaliação em lote.
- `core/unified_processing.py`: janela unificada para preparar dataset e treinar/avaliar.
- `core/env_check.py`: validação de ambiente sem importar nativos.

## Convenções de pastas
- `dataset/processed_oneclass/`: saída padronizada de features (parquet/npz).
- `model/model.pkl`: alias para o último modelo pronto.
- `model/manifest.json`: histórico de modelos treinados.
- `results_oneclass/`: métricas e imagens.
- `logs/`: logs rotativos e de treinamento.

## Dependências externas
- Conexões ODBC/SQL (em `db/mssql_connection.py`) são opcionais; quando indisponíveis, a UI e o core usam `storage/evaluations.db` e arquivos locais.

## Estrutura recomendada para novos módulos
- Coloque lógica de apresentação na pasta `ui/` com submódulos focados (ex.: `ui/chips.py`).
- Coloque lógica de negócio e computação em `core/`.
- Crie helpers transversais em `common/`.
- Atualize este documento e `docs/convenções.md` ao introduzir novas categorias.