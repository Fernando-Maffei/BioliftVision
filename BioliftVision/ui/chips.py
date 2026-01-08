# ui/chips.py
# Componentes e utilitários para os chips de status usados no painel direito.

from PyQt5.QtWidgets import QLabel, QSizePolicy, QGridLayout
from PyQt5.QtCore import Qt
import ui.style as ui_style


def make_chip(text: str) -> QLabel:

    lbl = QLabel(text)
    lbl.setAlignment(Qt.AlignCenter)
    lbl.setMinimumHeight(28)
    lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
    lbl.setStyleSheet(
        "border-radius: 14px; padding: 4px 10px;"
        f"background-color: {ui_style.SURFACE_COLOR};"
        f"color: {ui_style.TEXT_COLOR}; font-weight: 600; font-size: 11px;"
    )
    lbl.setWordWrap(False)
    return lbl


def update_chips_grid(grid: QGridLayout, chip_person: QLabel, chip_ai: QLabel, chip_judge: QLabel, available_w: int) -> None:
  
    if not grid or not chip_person or not chip_ai or not chip_judge:
        return
    try:
        chip_w = (
            chip_person.sizeHint().width() +
            chip_ai.sizeHint().width() +
            chip_judge.sizeHint().width() +
            2 * grid.spacing()
        )
        # Reposiciona conforme a largura disponível
        grid.removeWidget(chip_person)
        grid.removeWidget(chip_ai)
        grid.removeWidget(chip_judge)
        if available_w < chip_w + 40:
            grid.addWidget(chip_person, 0, 0)
            grid.addWidget(chip_ai, 0, 1)
            grid.addWidget(chip_judge, 1, 1)
        else:
            grid.addWidget(chip_person, 0, 0)
            grid.addWidget(chip_ai, 0, 1)
            grid.addWidget(chip_judge, 0, 2)
    except Exception:
       
        pass