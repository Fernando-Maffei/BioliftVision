import os
import time
import subprocess
import math
from typing import Optional
from PyQt5.QtCore import Qt, QProcess, QTimer
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QFileDialog, QPlainTextEdit, QProgressDialog, QMessageBox,
    QSizePolicy, QDialog
)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor
from common.paths import app_root, resource_path
from ui.style import get_global_styles


class TrainingWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Treinamento - Processar Vídeos")
        self.setGeometry(220, 140, 960, 700)
        ico_path = resource_path(os.path.join('ui', 'icon_hotbar.ico'))
        png_path = resource_path(os.path.join('ui', 'icon_hotbar.png'))
        if os.path.exists(ico_path):
            self.setWindowIcon(QIcon(ico_path))
        else:
            self.setWindowIcon(QIcon(png_path))
        self.setStyleSheet(get_global_styles())

        self.selected_dir: Optional[str] = None
        self.progress: Optional[QProgressDialog] = None
        self._progress_is_determinate = False
        self._proc: Optional[QProcess] = None
        self._cancelled: bool = False
        self._current_phase: str = ""

        central = QWidget()
        outer = QVBoxLayout(central)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(18)

        hero = QLabel("Selecione a pasta com vídeos para treinamento")
        hero.setObjectName("sectionTitle")
        hero.setAlignment(Qt.AlignCenter)
        outer.addWidget(hero)

        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(12)

        path_row = QHBoxLayout()
        self.lbl_dir = QLabel("Nenhuma pasta selecionada")
        self.lbl_dir.setObjectName("caption")
        self.lbl_dir.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_choose = QPushButton("Selecionar Pasta de Vídeos")
        btn_choose.setObjectName("primary")
        def _do_choose():
            d = QFileDialog.getExistingDirectory(self, "Selecionar pasta de vídeos", app_root())
            if d:
                self.selected_dir = d
                self.lbl_dir.setText(d)
                self.btn_extract.setEnabled(True)
                self.btn_train.setEnabled(True)
        btn_choose.clicked.connect(_do_choose)
        path_row.addWidget(self.lbl_dir)
        path_row.addWidget(btn_choose)
        card_layout.addLayout(path_row)

        actions = QHBoxLayout()
        self.btn_extract = QPushButton("Extrair e Gerar Parquet")
        self.btn_extract.setObjectName("primary")
        self.btn_extract.setEnabled(False)
        self.btn_extract.clicked.connect(self._start_extraction)
        self.btn_train = QPushButton("Treinar Modelo")
        self.btn_train.setObjectName("primary")
        self.btn_train.setEnabled(False)
        self.btn_train.clicked.connect(self._train_from_latest)
        actions.addStretch(1)
        actions.addWidget(self.btn_extract)
        actions.addWidget(self.btn_train)
        actions.addStretch(1)
        card_layout.addLayout(actions)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMinimumHeight(220)
        card_layout.addWidget(self.log_view)

        outer.addWidget(card)
        self.setCentralWidget(central)

    def _choose_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Selecionar pasta de vídeos", app_root())
        if d:
            self.selected_dir = d
            self.lbl_dir.setText(d)
            self.btn_extract.setEnabled(True)
            self.btn_train.setEnabled(True)

    def _start_extraction(self):
        if not self.selected_dir:
            QMessageBox.warning(self, "Processamento", "Selecione uma pasta de vídeos.")
            return
        self._cancelled = False
        self._current_phase = "extraction"
        self._show_progress("Processando vídeos e gerando parquet...")
        proc = QProcess(self)
        try:
            proc.setWorkingDirectory(app_root())
        except Exception:
            pass
        proc.readyReadStandardOutput.connect(self._on_output)
        proc.readyReadStandardError.connect(self._on_output)
        proc.finished.connect(self._on_finished)

        root = app_root()
        py310 = os.path.join(root, 'venv310', 'Scripts', 'python.exe')
        pyvenv = os.path.join(root, 'venv', 'Scripts', 'python.exe')
        python_cmd = py310 if os.path.exists(py310) else pyvenv if os.path.exists(pyvenv) else os.sys.executable

        out_base = os.path.join(root, 'dataset', 'processed_oneclass')
        code = (
            "import os, json, time;"
            "from pathlib import Path;"
            "from core.keypoints import process_correct_movements;"
            f"base=Path(r'{root}');inp=Path(r'{self.selected_dir}');out=Path(r'{out_base}');"
            "out.mkdir(parents=True, exist_ok=True);"
            "man=out/'manifest.json';hist=[];"
            "\nfor d in inp.iterdir():\n"
            "    if d.is_dir():\n"
            "        ex=d.name\n"
            "        vid_ext={'.mp4','.avi','.mov','.mkv'}\n"
            "        has=False\n"
            "        for r,_,fs in os.walk(str(d)):\n"
            "            if any(os.path.splitext(f)[1].lower() in vid_ext for f in fs):\n"
            "                has=True;break\n"
            "        if not has: continue\n"
            "        dest=out/ex\n"
            "        dest.mkdir(parents=True, exist_ok=True)\n"
            "        df=process_correct_movements(str(d), str(dest))\n"
            "        pq=dest/'correct_movements.parquet'\n"
            "        if pq.exists():\n"
            "            new=dest/(ex+'.parquet')\n"
            "            try:\n"
            "                if new.exists():\n"
            "                    new.unlink()\n"
            "            except Exception: pass\n"
            "            pq.replace(new)\n"
            "            hist.append({'exercise':ex,'path':str(new),'ts':time.strftime('%Y%m%d-%H%M%S')})\n"
            "\ntry:\n"
            "    old=[]\n"
            "    if man.exists(): old=json.load(open(man,'r',encoding='utf-8'))\n"
            "    old.extend(hist)\n"
            "    open(man,'w',encoding='utf-8').write(json.dumps(old,ensure_ascii=False,indent=2))\n"
            "except Exception: pass\n"
        )
        proc.start(python_cmd, ['-c', code])
        self._proc = proc

    def _train_from_latest(self):
        root = app_root()
        import glob
        base = os.path.join(root, 'dataset', 'processed_oneclass')
        pats = glob.glob(os.path.join(base, '**', '*.parquet'), recursive=True)
        if not pats:
            QMessageBox.information(self, "Treinamento", "Nenhum parquet encontrado.")
            return
        pats.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        latest = pats[0]

        self._cancelled = False
        self._current_phase = "training"
        self._show_progress("Treinando modelo...")
        proc = QProcess(self)
        try:
            proc.setWorkingDirectory(root)
        except Exception:
            pass
        proc.readyReadStandardOutput.connect(self._on_output)
        proc.readyReadStandardError.connect(self._on_output)
        proc.finished.connect(self._on_finished)

        py310 = os.path.join(root, 'venv310', 'Scripts', 'python.exe')
        pyvenv = os.path.join(root, 'venv', 'Scripts', 'python.exe')
        python_cmd = py310 if os.path.exists(py310) else pyvenv if os.path.exists(pyvenv) else os.sys.executable
        script = os.path.join(root, 'core', 'train_model.py')
        proc.start(python_cmd, [script, '--dataset-file', latest])
        self._proc = proc

    def _show_progress(self, text: str):
        if getattr(self, 'progress', None):
            try:
                if hasattr(self.progress, 'spinner'):
                    self.progress.spinner.stop()
            except Exception:
                pass
            self.progress.close()
        dlg = LoadingDialog(text, self)
        try:
            dlg.btn_cancel.clicked.connect(self._cancel_process)
        except Exception:
            pass
        self.progress = dlg
        self._progress_is_determinate = False
        dlg.show()

    def _close_progress(self):
        if getattr(self, 'progress', None):
            try:
                if hasattr(self.progress, 'spinner'):
                    self.progress.spinner.stop()
            except Exception:
                pass
            self.progress.close()
            self.progress = None
            self._progress_is_determinate = False

    def _append_log(self, msg: str):
        if hasattr(self, 'log_view') and self.log_view:
            self.log_view.appendPlainText(msg)

    def _on_output(self):
        try:
            if getattr(self, '_cancelled', False):
                return
            proc = self.sender()
            out = bytes(proc.readAllStandardOutput()).decode('utf-8', 'ignore')
            err = bytes(proc.readAllStandardError()).decode('utf-8', 'ignore')
            if out:
                self._append_log(out.strip())
            if err:
                self._append_log(err.strip())
        except Exception:
            pass

    def _on_finished(self):
        self._close_progress()
        self.btn_extract.setEnabled(bool(self.selected_dir))
        self.btn_train.setEnabled(bool(self.selected_dir))
        self._proc = None
        phase = self._current_phase
        self._current_phase = ""
        try:
            from common.paths import model_file
            if phase == "training":
                if os.path.exists(model_file()):
                    QMessageBox.information(self, "Treinamento", "Treinamento concluído com sucesso.")
                else:
                    QMessageBox.warning(self, "Treinamento", "Treinamento finalizado, modelo não encontrado.")
        except Exception:
            pass

    def _cancel_process(self):
        try:
            self._cancelled = True
            proc = getattr(self, '_proc', None)
            if proc:
                try:
                    proc.terminate()
                    proc.waitForFinished(2000)
                except Exception:
                    pass
                try:
                    pid = int(proc.processId())
                    if pid > 0 and os.name == 'nt':
                        try:
                            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    proc.kill()
                except Exception:
                    pass
            ts = time.strftime("%Y-%m-%d %H:%M:%S")
            try:
                from common.logger import log_info
                log_info(f"Cancelamento solicitado em {ts}")
            except Exception:
                pass
            self._append_log(f"[{ts}] Cancelamento efetuado.")
            try:
                QMessageBox.information(self, "Cancelado", "Operação cancelada com sucesso.")
            except Exception:
                pass
        finally:
            self._close_progress()
            self.btn_extract.setEnabled(bool(self.selected_dir))
            self.btn_train.setEnabled(bool(self.selected_dir))
            self._proc = None

class Spinner(QWidget):
    def __init__(self, size: int = 36):
        super().__init__()
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
            a = (self._angle + i * 30) * 3.14159265 / 180.0
            x = cx + int((r - 6) * math.cos(a))
            y = cy + int((r - 6) * math.sin(a))
            alpha = int(255 * (i + 1) / 12)
            p.setBrush(QColor(59, 130, 246, alpha))
            p.setPen(Qt.NoPen)
            p.drawEllipse(x - 4, y - 4, 8, 8)

class LoadingDialog(QDialog):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BioLiftVision")
        self.setWindowModality(Qt.ApplicationModal)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)
        title = QLabel(text)
        title.setAlignment(Qt.AlignCenter)
        sp = Spinner(40)
        sp.start()
        self.spinner = sp
        btn = QPushButton("Cancelar")
        self.btn_cancel = btn
        lay.addWidget(title)
        lay.addWidget(sp, alignment=Qt.AlignCenter)
        lay.addWidget(btn, alignment=Qt.AlignCenter)