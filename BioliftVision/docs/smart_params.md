# Parâmetros Inteligentes (Stride, Max Frames, Workers)

Este módulo implementa seleção automática inteligente dos parâmetros de processamento na tela **Processamento Unificado**, com possibilidade de sobrescrita manual por meio de um toggle intuitivo.

## Objetivos
- Sugerir `stride`, `max_frames` e `workers` com base em:
  - CPU disponível (`os.cpu_count`) e formato de saída
  - FPS estimado do primeiro vídeo encontrado (metadados via OpenCV)
  - Histórico recente de seleções do usuário (persistido em `storage/user_prefs.json`)
- Garantir respostas < 200ms e animações ≤ 300ms
- Aderir a WCAG 2.1 AA (acessibilidade por labels, tooltips e navegação por teclado)

## Componentes
- `ContextAdvisor`: carrega/salva histórico e calcula sugestões rápidas
- UI: `Seleção Automática` (checkbox) + três controles com feedback visual
  - Tooltip com motivo da sugestão
  - Destaque com borda (animação 250ms) quando automático
  - Desativando automático habilita ajuste manual

## Heurísticas
- `workers`: 50% dos núcleos (mín. 2, máx. 8)
- `stride`: 8 (fps≤24), 10 (fps≈30), 12 (fps≥60)
- `max_frames`: depende da quantidade de vídeos encontrada (≤80 itens inspecionados)
  - >40 vídeos: 120
  - >10 vídeos: 150
  - caso contrário: 150 ou 180 se fps≤24
- Formato `parquet` favorece `stride≥8` e `max_frames≤180`
- Histórico recente (até 50 entradas) sobrepõe heurísticas com o valor mais comum

## Persistência
- `storage/user_prefs.json` guarda até 200 seleções para evitar IO pesado

## Testes
- A lógica do `ContextAdvisor` foi validada originalmente com casos cobrindo sugestão sem histórico, influência do histórico e poda de armazenamento. Caso deseje reintroduzir testes, recomendo criar casos unitários focados nesses três cenários.

## Uso na aplicação
- Ao iniciar processamento, a seleção usada é gravada (auto ou manual), retroalimentando as sugestões futuras.

## Acessibilidade e usabilidade
- Labels, `aria-label` e tooltips descritivos
- Animações discretas (≤300ms) e contraste adequado
- Navegação por teclado compatível com os controles padrão
