from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QPixmap, QPainter, QColor
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QWidget
import math
from common.paths import resource_path


class Spinner(QWidget):
    def __init__(self, size: int = 40, parent=None):
        super().__init__(parent)
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.setInterval(80)
        self._timer.timeout.connect(self._tick)
        self._size = size
        self.setFixedSize(self._size, self._size)

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def _tick(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = min(self.width(), self.height()) // 2
        cx = self.width() // 2
        cy = self.height() // 2
        for i in range(12):
            a = (self._angle + i * 30) * math.pi / 180.0
            x = cx + int((r - 6) * math.cos(a))
            y = cy + int((r - 6) * math.sin(a))
            alpha = int(255 * (i + 1) / 12)
            p.setBrush(QColor(54, 194, 255, alpha))
            p.setPen(Qt.NoPen)
            p.drawEllipse(x - 4, y - 4, 8, 8)


class SplashDialog(QDialog):
    """Tela de splash com imagem, mensagem e indicador circular de carregamento."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint)
        self.setModal(False)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Imagem de fundo ocupando toda a área
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(True)
        img_path = resource_path('ui/tela_loading.png')
        pix = QPixmap(img_path)
        if pix.isNull():
            pix = QPixmap(resource_path('ui/icon_app.png'))
        self.image_label.setPixmap(pix)
        layout.addWidget(self.image_label)

        # Overlay transparente para texto e barra por cima da imagem
        self.overlay = QWidget(self.image_label)
        self.overlay.setAttribute(Qt.WA_TranslucentBackground, True)
        ovl = QVBoxLayout(self.overlay)
        ovl.setContentsMargins(64, 32, 64, 56)
        ovl.setSpacing(12)
        ovl.addStretch(5)

        self.spinner = Spinner(40, self.overlay)
        self.spinner.start()
        ovl.addWidget(self.spinner, alignment=Qt.AlignCenter)

        self.message_label = QLabel("Carregando...")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setObjectName("caption")
        ovl.addWidget(self.message_label)
        ovl.addStretch(1)

        self.resize(720, 480)
        self._update_overlay_geometry()

    def set_message(self, text: str):
        try:
            self.message_label.setText(text)
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
        except Exception:
            pass

    def set_progress(self, value: int):
        try:
            from PyQt5.QtWidgets import QApplication
            app = QApplication.instance()
            if app:
                app.processEvents()
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_overlay_geometry()

    def _update_overlay_geometry(self):
        try:
            if self.overlay and self.image_label:
                self.overlay.setGeometry(0, 0, self.image_label.width(), self.image_label.height())
        except Exception:
            pass