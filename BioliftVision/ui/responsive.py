from typing import Tuple


def compute_right_panel_width(viewport_w: int) -> Tuple[int, int, int]:
    """Calcula largura alvo do painel direito com base em breakpoints.

    Retorna (target, min_w, max_w) para permitir depuração/telemetria futura.
    Ajustado para dar mais espaço à aba de notas em telas menores.
    """
    vw = max(1, int(viewport_w or 1))
    ratio = 0.42 if vw < 1280 else (0.40 if vw < 1600 else 0.38)
    min_w = 540 if vw < 1280 else 500
    if vw >= 1920:
        max_w = 880
    elif vw >= 1600:
        max_w = 820
    else:
        max_w = 740
    target = int(max(min_w, min(max_w, vw * ratio)))
    return target, min_w, max_w


def clamp_left_width(total_w: int, right_w: int, margins_lr: int, required_w: int, *, min_w: int = 360) -> int:
    """Limita larguras de elementos do lado esquerdo para não invadir o painel direito.

    - `total_w`: largura total da janela
    - `right_w`: largura fixa/atual do painel direito
    - `margins_lr`: soma das margens esquerda/direita aplicadas
    - `required_w`: largura desejada com base em sizeHints dos controles
    - `min_w`: largura mínima confortável para manter legibilidade
    """
    total_w = int(max(1, total_w))
    right_w = int(max(min_w, right_w))
    left_available = max(min_w, total_w - right_w - int(margins_lr or 0))
    return max(min_w, min(int(required_w or min_w), left_available))