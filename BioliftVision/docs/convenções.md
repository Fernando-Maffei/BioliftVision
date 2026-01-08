# Convenções de Nomenclatura e Organização

Estas convenções garantem consistência e facilidade de manutenção.

## Nomes de arquivos e módulos
- Módulos Python: `snake_case.py` (ex.: `responsive.py`, `chips.py`).
- Classes PyQt5: `CamelCase` (ex.: `MainWindow`, `TrainingWindow`).
- Funções e variáveis: `snake_case` (ex.: `update_chips_grid`, `right_panel_width`).
- Constantes: `UPPER_SNAKE_CASE` (ex.: `SURFACE_COLOR`, `BG_COLOR`).

## Estrutura de componentes
- UI:
  - Componentes reutilizáveis em arquivos próprios (ex.: `ui/chips.py`).
  - Utilitários transversais de UI em `ui/responsive.py`.
  - Estilos e paleta em `ui/style.py`.
- Core:
  - Cálculo e regras (keypoints, ângulos, scoring, treino, avaliação).
- Common:
  - `logger`, `paths`, helpers gerais (sem dependências de UI).

## Handlers e atualizações
- Eventos de janela: `on_<evento>` ou `_update_<alvo>` (privados) em `ui/interface.py`.
- Layouts: centralize a lógica em utilitários quando possível: `update_chips_grid`, `clamp_left_width`.

## Status e chips
- Status válidos: `valid`, `invalid`, `pending`.
- Cores por status mapeadas via `ui/style.py` e aplicadas por `chips.make_chip()`.

## Responsividade
- Painel direito calculado via `responsive.compute_right_panel_width()` com breakpoints.
- Larguras à esquerda limitadas por `responsive.clamp_left_width()`.
- Alinhamento padrão dos controles inferiores: à esquerda, com limites de largura.

## Importações
- Evite importações circulares. Mantenha `ui/interface.py` como orquestrador e os componentes em módulos próprios.
- Use caminhos relativos ao pacote (`from ui.chips import make_chip`).

## Documentação
- Ao introduzir componente/módulo, atualize:
  - `docs/estrutura.md`
  - `docs/convenções.md`
  - `docs/guia_manutencao.md` (se houver impactos em manutenção)

## Testes e validação
- Adicione testes focados quando alterar lógica do core.
- Para mudanças de UI, valide visualmente executando o app e verificando logs em `logs/`.