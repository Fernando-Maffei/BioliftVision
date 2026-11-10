from ui.style import apply_theme, get_global_styles
from common.paths import resource_path, models_dir
from common.logger import log_info, log_warning
import mediapipe as mp
from core.scoring_system import EnhancedScoringSystem
from core.angulos import AdvancedAngleCalculator
import ui.style as ui_style
from ui.settings import SettingsDialog
import sys
import os
import cv2
import joblib
import numpy as np
import time
import math
from core.run_model import latest_model_info
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QVBoxLayout,
    QHBoxLayout, QFileDialog, QComboBox, QSpinBox, QDoubleSpinBox, QTreeWidget, QTreeWidgetItem,
    QFrame, QGraphicsOpacityEffect, QSizePolicy, QScrollArea, QCheckBox, QAction, QGraphicsBlurEffect,
    QTabWidget, QTextEdit, QFormLayout, QCompleter, QAbstractSpinBox, QInputDialog, QToolBar, QMessageBox,
    QSlider, QGridLayout
)
from PyQt5.QtCore import QStringListModel
from PyQt5.QtWidgets import QCompleter
import os
import json
from PyQt5.QtGui import QPixmap, QImage, QIcon, QPainter, QColor, QPen
from PyQt5.QtCore import QTimer, Qt, pyqtSignal, QSize, QRect, QPoint
from PyQt5.QtWidgets import QToolTip
from common.player_utils import compute_interval_ms, clamp_frame_index
from ui.responsive import compute_right_panel_width
from storage.persistence import init_db, save_attempt, fetch_attempts

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


try:
    import pyqtgraph as pg
    HAS_PYQTGRAPH = True
except Exception:
    HAS_PYQTGRAPH = False

SHOW_ANGLE_PLOT = False

# ===== CONFIGURAÇÕES DE TELA =====
VIDEO_WIDTH, VIDEO_HEIGHT = 900, 650 
COLOR_VALID, COLOR_INVALID, COLOR_NEUTRAL = "#22C55E", "#EF4444", ui_style.MUTED_COLOR

# ===== BOTÃO ANIMADO SIMPLES =====


class SimpleAnimatedButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.PointingHandCursor)
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_effect.setOpacity(1.0)

    def enterEvent(self, event):
        
        self.opacity_effect.setOpacity(0.96)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.opacity_effect.setOpacity(1.0)
        super().leaveEvent(event)

# ===== INTERFACE PRINCIPAL =====


class VideoAnalysisApp(QMainWindow):
    analysisUpdated = pyqtSignal(dict)
    windowStateVerified = pyqtSignal(bool)

    def __init__(self, model_path: str):
        super().__init__()
        self.setWindowTitle("BioLiftVision")
        self.setMinimumSize(1400, 900)
       
        try:
            from PyQt5.QtGui import QPixmap, QIcon
            ico_path = resource_path('ui/icon_hotbar.ico')
            png_path = resource_path('ui/icon_hotbar.png')
            if not os.path.exists(ico_path) and os.path.exists(png_path):
                try:
                    pix = QPixmap(png_path)
                    if not pix.isNull():
                        pix.save(ico_path, "ICO")
                except Exception:
                    pass
            if os.path.exists(ico_path):
                self.setWindowIcon(QIcon(ico_path))
            else:
                self.setWindowIcon(QIcon(png_path))
        except Exception:
            pass
        # Aplicar tema atual do ambiente antes de montar estilos
        self.current_theme = os.environ.get('POWERLIFT_THEME', 'AuroraDark')
        apply_theme(self.current_theme)
        self.setStyleSheet(get_global_styles() + self._get_stylesheet())
        self._load_model(model_path)
        self._init_state()

        self._player_controls_locked = False
        self._init_ui()
        try:
            init_db()
        except Exception:
            pass

    def _get_stylesheet(self):
        return """
        QToolTip {
            background-color: #111827;
            color: #E5E7EB;
            border: 1px solid #374151;
            padding: 4px 8px;
            border-radius: 6px;
        }
        """

    def _load_model(self, model_path):
        try:

            self.current_model_path = model_path or ''
            if not model_path:
                log_info("Iniciando sem modelo: análise visual ativa.")
                self.model = None
                self.feature_names = []
                self.scaler = None
                self.imputer = None
            else:
                model_data = joblib.load(model_path)
                self.model = model_data['model']
                self.feature_names = model_data['features']
                self.scaler = model_data.get('scaler')
                self.imputer = model_data.get('imputer')
                log_info(f"Modelo carregado de '{model_path}'")
            # Captura informações do último manifest
            try:
                self.model_info = latest_model_info() or {}
            except Exception:
                self.model_info = {}

            self.angle_calculator = AdvancedAngleCalculator()
            self.enhanced_scoring = EnhancedScoringSystem()

            self.mp_holistic = mp.solutions.holistic
            self.mp_drawing = mp.solutions.drawing_utils
            self.holistic = self.mp_holistic.Holistic(
                min_detection_confidence=0.91,
                min_tracking_confidence=0.65,
                model_complexity=1
            )

        except Exception as e:
            log_warning(
                f"Falha ao carregar modelo '{model_path}': {e}. Executando análise visual.")
            self.model = None
            self.feature_names = []
            self.scaler = None
            self.imputer = None
            self.current_model_path = ''
            self.angle_calculator = AdvancedAngleCalculator()
            self.enhanced_scoring = EnhancedScoringSystem()
            self.mp_holistic = mp.solutions.holistic
            self.mp_drawing = mp.solutions.drawing_utils
            self.holistic = self.mp_holistic.Holistic(
                min_detection_confidence=0.91,
                min_tracking_confidence=0.65,
                model_complexity=1
            )
            try:
                self.model_info = latest_model_info() or {}
            except Exception:
                self.model_info = {}

    def _current_exercise_key(self):
        try:
            txt = self.exercise_combo.currentText().lower()
            if 'agachamento' in txt:
                return 'squat'
            if 'levantamento' in txt or 'terra' in txt:
                return 'deadlift'
        except Exception:
            pass
        return 'unknown'

    def _model_path_for_mode(self, mode: str) -> str:
        try:
            base = models_dir()
            if mode == 'default':
                return os.path.join(base, 'model.pkl')
            if mode == 'squat':
                p = os.path.join(base, 'model_squat.pkl')
                return p if os.path.exists(p) else os.path.join(base, 'model.pkl')
            if mode == 'deadlift':
                p = os.path.join(base, 'model_deadlift.pkl')
                return p if os.path.exists(p) else os.path.join(base, 'model.pkl')
            if mode == 'auto':
                ex = self._current_exercise_key()
                if ex in ('squat', 'deadlift'):
                    p = os.path.join(base, f'model_{ex}.pkl')
                    return p if os.path.exists(p) else os.path.join(base, 'model.pkl')
                return os.path.join(base, 'model.pkl')
        except Exception:
            pass
        return ''

    def _switch_model_mode(self, mode: str):
        try:
            mpth = self._model_path_for_mode(mode)
            # Evitar recarregar o mesmo modelo
            if hasattr(self, 'current_model_path') and mpth == self.current_model_path:
                pass
            else:
                self._load_model(mpth)
            # Feedback de status
            if hasattr(self, 'status_label'):
                try:
                    lbl = {
                        'auto': 'Modelo: Auto por exercício',
                        'squat': 'Modelo: Agachamento',
                        'deadlift': 'Modelo: Levantamento Terra',
                        'default': 'Modelo: Geral'
                    }.get(mode, 'Modelo: Visual')
                    self.status_label.setText(lbl)
                except Exception:
                    pass
            # Atualiza exibição do nome do modelo carregado
            try:
                if hasattr(self, 'model_name_label'):
                    model_name = os.path.basename(mpth) if mpth else 'Visual'
                    ex = self._current_exercise_key()
                    ex_disp = {
                        'squat': 'Agachamento',
                        'deadlift': 'Levantamento Terra'
                    }.get(ex, 'Desconhecido')
                    self.model_name_label.setText(f"{ex_disp} → {model_name}")
                self.current_model_path = mpth or ''
            except Exception:
                pass
        except Exception as e:
            log_warning(f"Falha ao alternar modelo: {e}")

    # ===== Integração simples do modelo treinado =====
    def _recognized_feature_map(self):
        """Mapa de features reconhecidas para inferência.
        Alinha com feature_config do treino (coords, visibilidade, vel/acc, índices).
        """
        lm = getattr(self, 'last_lm', {})
        vel = getattr(self, 'last_vel', {})
        acc = getattr(self, 'last_acc', {})

        def coord(j, ax):
            return lambda a, s: (lm.get(j, {}) or {}).get(ax)

        def vis(j):
            return lambda a, s: (lm.get(j, {}) or {}).get('visibility')

        def v(j, ax):
            return lambda a, s: vel.get((j, ax))

        def a_(j, ax):
            return lambda a, s: acc.get((j, ax))

        fmap = {}
        joints = [
            'NOSE', 'LEFT_EAR', 'RIGHT_EAR',
            'LEFT_SHOULDER', 'RIGHT_SHOULDER',
            'LEFT_HIP', 'RIGHT_HIP',
            'LEFT_KNEE', 'RIGHT_KNEE',
            'LEFT_ANKLE', 'RIGHT_ANKLE',
        ]
        for j in joints:
            fmap[f"{j}_x"] = coord(j, 'x')
            fmap[f"{j}_y"] = coord(j, 'y')
            fmap[f"{j}_z"] = coord(j, 'z')
            fmap[f"{j}_visibility"] = vis(j)

        # Velocidades e acelerações dos pontos do treino
        fmap['LEFT_HIP_x_velocity'] = v('LEFT_HIP', 'x')
        fmap['LEFT_HIP_x_acceleration'] = a_('LEFT_HIP', 'x')
        fmap['LEFT_HIP_y_velocity'] = v('LEFT_HIP', 'y')
        fmap['LEFT_HIP_y_acceleration'] = a_('LEFT_HIP', 'y')

        fmap['RIGHT_HIP_x_velocity'] = v('RIGHT_HIP', 'x')
        fmap['RIGHT_HIP_x_acceleration'] = a_('RIGHT_HIP', 'x')
        fmap['RIGHT_HIP_y_velocity'] = v('RIGHT_HIP', 'y')
        fmap['RIGHT_HIP_y_acceleration'] = a_('RIGHT_HIP', 'y')

        fmap['LEFT_SHOULDER_x_velocity'] = v('LEFT_SHOULDER', 'x')
        fmap['LEFT_SHOULDER_x_acceleration'] = a_('LEFT_SHOULDER', 'x')
        fmap['LEFT_SHOULDER_y_velocity'] = v('LEFT_SHOULDER', 'y')
        fmap['LEFT_SHOULDER_y_acceleration'] = a_('LEFT_SHOULDER', 'y')

        # Índices derivados
        def torso_stability(a, s):
            ly = (lm.get('LEFT_SHOULDER', {}) or {}).get('y')
            ry = (lm.get('RIGHT_SHOULDER', {}) or {}).get('y')
            if ly is None or ry is None:
                return None
            mean_y = (ly + ry) / 2.0
            var_y = ((ly - mean_y) ** 2 + (ry - mean_y) ** 2) / 2.0
            return 1.0 / (var_y + 1e-6)

        def balance_index(a, s):
            lh = lm.get('LEFT_HIP', {}) or {}
            rh = lm.get('RIGHT_HIP', {}) or {}
            la = lm.get('LEFT_ANKLE', {}) or {}
            ra = lm.get('RIGHT_ANKLE', {}) or {}
            hip_cx = ((lh.get('x') or 0.0) + (rh.get('x') or 0.0)) / 2.0
            ank_cx = ((la.get('x') or 0.0) + (ra.get('x') or 0.0)) / 2.0
            return abs(hip_cx - ank_cx)

        fmap['torso_stability'] = torso_stability
        fmap['balance_index'] = balance_index

        # Mantém ângulos e relações quando existirem no modelo
        fmap['knee_angle'] = lambda a, s: a.get('knee_angle')
        fmap['hip_angle'] = lambda a, s: a.get('hip_angle')
        fmap['torso_angle'] = lambda a, s: a.get('torso_angle')
        fmap['back_angle'] = lambda a, s: a.get('back_angle')
        fmap['stability'] = lambda a, s: s
        fmap['knee_hip_ratio'] = lambda a, s: (a.get('knee_angle') or 0) / max(1e-6, (a.get('hip_angle') or 1e-6))
        fmap['hip_torso_ratio'] = lambda a, s: (a.get('hip_angle') or 0) / max(1e-6, (a.get('torso_angle') or 1e-6))

        return fmap

    def _build_model_vector(self, angles: dict, stability: float):
        """Constrói vetor de features na ordem esperada pelo modelo.
        Retorna (X, used_features) ou (None, []).
        """
        if not self.model or not self.feature_names:
            return None, []
        fmap = self._recognized_feature_map()
        used = []
        vals = []
        for fname in self.feature_names:
            if fname in fmap:
                v = fmap[fname](angles, stability)
                vals.append(np.nan if v is None else float(v))
                used.append(fname)
            else:
                # feature não derivável em tempo real
                vals.append(np.nan)
                used.append(fname)
        if len(used) == 0:
            return None, []
        X = np.array([vals], dtype=np.float64)
        try:
            if self.imputer is not None:
                X = self.imputer.transform(X)
            else:
                # Preenche NaN com zero como fallback leve
                X = np.nan_to_num(X, nan=0.0)
            if self.scaler is not None:
                X = self.scaler.transform(X)
        except Exception:
            pass
        return X, used

    def _evaluate_with_model(self, angles: dict, stability: float, exercise_label: str) -> dict | None:
        """Avaliação básica usando modelo OneClassSVM treinado.
        Mapeia decisão para um score/percentual simples e luzes IPF.
        """
        try:
            X, used = self._build_model_vector(angles, stability)
            if X is None:
                return None
            # Previsão: +1 normal, -1 anomalia
            pred = self.model.predict(X)[0]
            # Score contínuo
            try:
                s = float(self.model.decision_function(X)[0])
            except Exception:
                s = 0.0
            # Normaliza via sigmoide para percentual 0..100
            perc = float(100.0 / (1.0 + np.exp(-s)))
            valid = bool(pred == 1)
            lights = ['white', 'white', 'white'] if valid else [
                'red', 'red', 'red']
            # Rótulo de qualidade simples
            if perc >= 80:
                quality = 'Excelente'
            elif perc >= 60:
                quality = 'Bom'
            elif perc >= 40:
                quality = 'Regular'
            else:
                quality = 'Muito Ruim'
            feedback = []
            if not valid:
                feedback.append('Anomalia detectada pelo modelo treinado')
            else:
                feedback.append(
                    'Movimento consistente segundo o modelo treinado')
            feedback.append(
                f"Features usadas: {min(len(used), 6)} de {len(self.feature_names)}")
            return {
                'valid': valid,
                'score': int(round(perc)),
                'max_score': 100,
                'lights': lights,
                'feedback': feedback,
                'quality': quality,
                'exercise': exercise_label,
            }
        except Exception:
            return None

    def _init_state(self):
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_frame)
        # Estado do player
        self.current_frame_index = 0
        self.total_frames = 0
        self.fps = 30.0
        self.base_interval_ms = 33
        self.playback_speed = 1.0
        self.is_fullscreen = False
        self._seeking = False
        self.last_prediction = None
        self.evaluations = []
        self.rep_start_time = None
        self.rep_start_confirm = 0
        self.rep_end_confirm = 0
        self.rep_confirm_frames_start = 2
        self.rep_confirm_frames_end = 2
        self.current_rep_data = []
        self.previous_angles = {}
        self.smoothed_angles = {}
        self.smoothing_alpha = 0.3
        self.rep_count = 0

        # Estados de landmarks para alinhar com features do treino
        self.last_lm = {}
        self.prev_lm = {}
        self.last_vel = {}
        self.last_acc = {}
        # Anotações por frame
        self.annotations = {}
        self.annotation_arm = False

        self.selected_person_id = None
        self.detected_people = []
        self.last_click_pos = None
        self.person_colors = [
            (0, 255, 0),    # Verde
            (255, 0, 0),    # Azul
            (0, 0, 255),    # Vermelho
            (255, 255, 0),  # Ciano
            (255, 0, 255),  # Magenta
            (0, 255, 255)   # Amarelo
        ]
        self.show_grid = True
        self.grid_rows = 3
        self.grid_cols = 2
        self.grid_thickness = 1
        self.grid_alpha = 0.25
        self.show_bar_path = False
        self.bar_path_points = []
        self.bar_path_thickness = 2
        self.bar_path_max_points = 600
        # Novos estados
        self.show_landmarks = True
        self.responsive_ratio = VIDEO_WIDTH / VIDEO_HEIGHT
        self.last_analysis = None
        # Estados para julgamento combinado e gráfico
        self.last_judge_decision = None 
        self.auto_result = None          
        self.angle_series = {
            'knee_angle': [],
            'hip_angle': [],
            'torso_angle': []
        }
        # Últimos dados para exibição ao juiz
        self.last_angles = None
        self.last_eval_summary = None

        self.camera_interrupted = False
        self._prev_frame_gray = None
        self._interruption_counter = 0
        self._freeze_diff_threshold = 0.001  
        self._freeze_min_frames = 15        

        self.always_show_evaluation = True

        self.use_model_inference = False

        # Buffer de aprendizado contínuo
        self._runtime_samples = []
        self._runtime_session_id = f"{int(time.time())}"
        self._runtime_buffer_limit = 200

        # Overlay de luzes IPF (opcional sobre o vídeo)
        self.show_ipf_lights_overlay = True
        self.ipf_overlay_duration_sec = 2.0
        self.ipf_overlay_fade_ms = 250
        self._ipf_lights_current = []  
        self._ipf_overlay_start_ms = 0
        self._ipf_overlay_until_ms = 0


    def _init_ui(self):
        central_widget = QWidget()
        central_widget.setObjectName("mainCentral")
        self.setCentralWidget(central_widget)
        # Fundo com imagem e blur semelhante ao Main
        bg_path = resource_path('ui/background.png').replace('\\', '/')
        self._bg_label = QLabel(self)
        self._bg_pixmap = QPixmap(bg_path)
        self._bg_label.setScaledContents(True)
        blur = QGraphicsBlurEffect(self._bg_label)
        blur.setBlurRadius(10)
        self._bg_label.setGraphicsEffect(blur)
        self._bg_label.setGeometry(self.rect())
        self._bg_label.lower()

        # Menu Aparência/Configurações
        menubar = self.menuBar()
        self.current_theme = os.environ.get('POWERLIFT_THEME', 'AuroraDark')
        # Atalho para alternar grade
        self.toggleGridAction = QAction("Alternar grade (G)", self)
        self.toggleGridAction.setShortcut("G")
        self.toggleGridAction.setCheckable(True)
        self.toggleGridAction.setChecked(self.show_grid)
        self.toggleGridAction.toggled.connect(self._toggle_grid)
        self.addAction(self.toggleGridAction)
        # Oculta ação de grade e desativa atalho
        self.toggleGridAction.setVisible(False)
        self.toggleGridAction.setEnabled(False)
        self.toggleGridAction.setShortcut("")

        # Atalho para trajetória da barra
        self.toggleBarPathAction = QAction("Alternar trajetória (B)", self)
        self.toggleBarPathAction.setShortcut("B")
        self.toggleBarPathAction.setCheckable(True)
        self.toggleBarPathAction.setChecked(self.show_bar_path)
        self.toggleBarPathAction.toggled.connect(self._toggle_bar_path)
        self.addAction(self.toggleBarPathAction)

        self.toggleBarPathAction.setVisible(False)
        self.toggleBarPathAction.setEnabled(False)
        self.toggleBarPathAction.setShortcut("")

        # Hotbar (toolbar superior)
        try:
            toolbar = QToolBar("Hotbar", self)
            toolbar.setMovable(False)
            toolbar.setIconSize(QSize(24, 24))
            toolbar.setStyleSheet(
                "QToolBar { background: rgba(14,17,22,180); border: none; padding: 6px; }")
            hotbar_icon_path = resource_path('ui/icon_hotbar.png')
            hotbar_action = QAction(
                QIcon(hotbar_icon_path), "BioLift Hotbar", self)
            hotbar_action.setEnabled(False)
            toolbar.addAction(hotbar_action)
            self.addToolBar(Qt.TopToolBarArea, toolbar)
            self.hotbar = toolbar
        except Exception:
            pass

        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        # ===== LADO ESQUERDO =====
        left_widget = QWidget()
        # Promove o left_widget a atributo para permitir posicionamento absoluto posterior
        self.left_widget = left_widget
        # Tornar a coluna esquerda expansível para melhor uso de espaço
        left_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setSpacing(12)

        # Área do vídeo
        # Mantém referência ao frame do vídeo para ajustar largura conforme o vídeo
        self.video_frame = QFrame()
        self.video_frame.setObjectName("sectionCard")
        # Borda externa para estabilizar visual e alinhar ao tamanho da tela
        try:
            self.video_frame.setStyleSheet("border: 1px solid #2A2A3A; border-radius: 8px;")
        except Exception:
            pass
        # Tornar a área de vídeo responsiva ao tamanho da janela
        self.video_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_layout = QVBoxLayout(self.video_frame)
        video_layout.setContentsMargins(10, 10, 10, 10)

        # Label original mantida para compatibilidade, porém oculta
        self.video_label = QLabel()
        self.video_label.setVisible(False)
        # Nova label independente para exibição do vídeo
        self.video_display = QLabel()
        self.video_display.setObjectName("videoDisplay")
        self.video_display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_display.setAlignment(Qt.AlignCenter)
        self.video_display.setStyleSheet(
            "background-color: #000000; border: 2px solid #3A3A4D; border-radius: 8px; color: #888888; font-size: 14px;")
        self.video_display.setScaledContents(False)
        self.video_display.setText("Vídeo não carregado")
        self.video_display.mousePressEvent = self._on_video_click

        # Modo travado de área de vídeo: mantém área fixa independente da proporção do vídeo
        self.lock_video_area = True
        self.fixed_video_ratio = 16.0 / 9.0 

        video_layout.addWidget(self.video_display)
        # ===== Barra do Player (abaixo do vídeo) =====
        player_controls = QWidget()
        # Guarda referência para usar altura real na reserva vertical
        self.player_controls = player_controls
        # Se controles estão travados, ocultar e manter altura zero
        if getattr(self, '_player_controls_locked', False):
            player_controls.setVisible(False)
            player_controls.setFixedHeight(0)
            player_controls.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        else:
            # Desvincula a largura da barra do player da área de vídeo
            player_controls.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        pc_vbox = QVBoxLayout(player_controls)
        pc_vbox.setContentsMargins(12, 10, 12, 10)
        pc_vbox.setSpacing(8)

        
        if not getattr(self, '_player_controls_locked', False):
           
            self.frame_slider = QSlider(Qt.Horizontal)
            self.frame_slider.setEnabled(False)
            self.frame_slider.setRange(0, 0)
            self.frame_slider.valueChanged.connect(self._on_slider_changed)
            self.frame_slider.sliderPressed.connect(self._on_slider_pressed)
            self.frame_slider.sliderReleased.connect(self._on_slider_released)
            self.frame_slider.setVisible(False)

           
            class YouTubeProgressBar(QWidget):
                seekRequested = pyqtSignal(int)  # índice de frame
                draggingStarted = pyqtSignal()
                draggingFinished = pyqtSignal()

                def __init__(self, parent=None):
                    super().__init__(parent)
                    # Aumenta altura para melhor toque e visual
                    self.setMinimumHeight(26)
                    self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
                    self._total = 0
                    self._value = 0
                    self._buffer = 0.0  # 0..1
                    self._fps = 30.0
                    self._dragging = False
                    self._bg = QColor('#2A2F3B')
                    self._bufferColor = QColor('#6B7280')  # cinza carregado
                    self._progressColor = QColor('#60A5FA')  # azul
                    self._thumbColor = QColor('#FFFFFF')
                    self._groove_margin = 12
                    self._groove_height = 8
                    self._tooltip_offset_y = 24  # distância acima do groove
                    self.setMouseTracking(True)

                def setTotal(self, total_frames: int):
                    self._total = max(0, int(total_frames))
                    self.update()

                def setFps(self, fps: float):
                    self._fps = max(1.0, float(fps or 30.0))

                def setValue(self, index: int):
                    self._value = max(0, int(index))
                    self.update()

                def setBuffer(self, percent: float):
                    self._buffer = max(0.0, min(1.0, float(percent or 0.0)))
                    self.update()

                def _format_time(self, seconds: float) -> str:
                    seconds = max(0.0, float(seconds or 0.0))
                    m = int(seconds // 60)
                    s = int(seconds % 60)
                    return f"{m}:{s:02d}"

                def _index_to_time_label(self, idx: int) -> str:
                    cur = (idx / self._fps) if self._fps > 0 else 0.0
                    tot = (self._total / self._fps) if self._fps > 0 else 0.0
                    return f"{self._format_time(cur)} / {self._format_time(tot)}"

                def paintEvent(self, e):
                    p = QPainter(self)
                    rect = self.rect()
                    # Groove de fundo
                    p.setPen(Qt.NoPen)
                    p.setBrush(self._bg)
                    p.drawRoundedRect(rect.adjusted(0, 6, 0, -6), 6, 6)

                    if rect.width() <= 6:
                        return

                    groove = QRect(
                        rect.left() + self._groove_margin,
                        rect.top() + rect.height()//2 - self._groove_height//2,
                        rect.width() - 2 * self._groove_margin,
                        self._groove_height,
                    )
                    # Buffer
                    buf_w = int(groove.width() * self._buffer)
                    if buf_w > 0:
                        buf_rect = QRect(groove.left(), groove.top(), buf_w, groove.height())
                        p.setBrush(self._bufferColor)
                        p.drawRect(buf_rect)

                    # Progresso
                    ratio = (self._value / self._total) if self._total > 0 else 0.0
                    prog_w = int(groove.width() * ratio)
                    if prog_w > 0:
                        prog_rect = QRect(groove.left(), groove.top(), prog_w, groove.height())
                        p.setBrush(self._progressColor)
                        p.drawRect(prog_rect)

                    # Thumb
                    thumb_x = groove.left() + prog_w
                    thumb_y = groove.center().y()
                    p.setBrush(self._thumbColor)
                    p.setPen(QPen(QColor('#1F2937')))
                    p.drawEllipse(QPoint(thumb_x, thumb_y), 5, 5)

                def _pos_to_index(self, x: int) -> int:
                    rect = self.rect()
                    groove = QRect(
                        rect.left() + self._groove_margin,
                        rect.top() + rect.height()//2 - self._groove_height//2,
                        rect.width() - 2 * self._groove_margin,
                        self._groove_height,
                    )
                    if groove.width() <= 0 or self._total <= 0:
                        return 0
                    x = max(groove.left(), min(x, groove.right()))
                    ratio = (x - groove.left()) / float(groove.width())
                    return int(ratio * (self._total - 1))

                def mousePressEvent(self, ev):
                    self._dragging = True
                    self.draggingStarted.emit()
                    idx = self._pos_to_index(ev.x())
                    self.setValue(idx)
                    self.seekRequested.emit(idx)
                    # Mostra tooltip ancorado acima do polegar com tempo atual/total
                    rect = self.rect()
                    groove = QRect(
                        rect.left() + self._groove_margin,
                        rect.top() + rect.height()//2 - self._groove_height//2,
                        rect.width() - 2 * self._groove_margin,
                        self._groove_height,
                    )
                    x = max(groove.left(), min(ev.x(), groove.right()))
                    tip_pos = self.mapToGlobal(QPoint(x, groove.top() - self._tooltip_offset_y))
                    QToolTip.showText(tip_pos, self._index_to_time_label(idx))

                def mouseMoveEvent(self, ev):
                    idx = self._pos_to_index(ev.x())
                    rect = self.rect()
                    groove = QRect(
                        rect.left() + self._groove_margin,
                        rect.top() + rect.height()//2 - self._groove_height//2,
                        rect.width() - 2 * self._groove_margin,
                        self._groove_height,
                    )
                    x = max(groove.left(), min(ev.x(), groove.right()))
                    tip_pos = self.mapToGlobal(QPoint(x, groove.top() - self._tooltip_offset_y))
                    QToolTip.showText(tip_pos, self._index_to_time_label(idx))
                    if self._dragging:
                        self.setValue(idx)
                        self.seekRequested.emit(idx)

                def mouseReleaseEvent(self, ev):
                    if self._dragging:
                        self._dragging = False
                        self.draggingFinished.emit()

            # instancia e conecta
            self.yt_bar = YouTubeProgressBar(self)
            pc_vbox.addWidget(self.yt_bar)
            self.yt_time_label = QLabel("0:00 / 0:00")
            self.yt_time_label.setStyleSheet(
                f"color: {ui_style.TEXT_COLOR}; font-size: 12px; font-weight: 600; padding: 0px;"
            )
            self.yt_time_label.setAlignment(Qt.AlignLeft)
            self.yt_time_label.setMinimumHeight(32)
            self.yt_time_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            yt_time_row = QHBoxLayout()
            yt_time_row.setContentsMargins(12, 0, 12, 0)
            yt_time_row.setSpacing(8)
            yt_time_row.setAlignment(Qt.AlignVCenter)
            yt_time_row.addWidget(self.yt_time_label, 0, Qt.AlignVCenter | Qt.AlignLeft)
            self._yt_time_group = yt_time_row

            # Sincroniza as duas barras
            self.frame_slider.valueChanged.connect(lambda v: self.yt_bar.setValue(int(v)))
            self.yt_bar.seekRequested.connect(lambda idx: self._seek_to_frame(int(idx)))
            self.yt_bar.draggingStarted.connect(self._on_slider_pressed)
            self.yt_bar.draggingFinished.connect(self._on_slider_released)

        # Linha de controles reorganizada em grupos para melhor alinhamento
        pc_row = QHBoxLayout()
        pc_row.setSpacing(8)
        pc_row.setContentsMargins(12, 0, 12, 0)
        pc_row.setAlignment(Qt.AlignCenter)

        # Insere a label de tempo no início da linha para alinhar com os botões
        if hasattr(self, '_yt_time_group'):
            pc_row.addLayout(self._yt_time_group)
            pc_row.addSpacing(12)

        # Grupo de navegação (voltar/iniciar/avançar)
        nav_group = QHBoxLayout()
        nav_group.setSpacing(8)
        nav_group.setContentsMargins(0, 0, 0, 0)
        nav_group.setAlignment(Qt.AlignCenter)

        # prev_frame_btn removido

        if not getattr(self, '_player_controls_locked', False):
            self.play_pause_btn = SimpleAnimatedButton("► Iniciar")
            self.play_pause_btn.setObjectName("playerControlBtn")
            self.play_pause_btn.setToolTip("Play/Pause")
            self.play_pause_btn.clicked.connect(self._toggle_play_pause)
            self.play_pause_btn.setFixedHeight(40)
            self.play_pause_btn.setMinimumWidth(110)
            self.play_pause_btn.setMaximumWidth(140)
            self.play_pause_btn.setStyleSheet(f"""
            QPushButton#playerControlBtn {{
                background-color: {ui_style.PRIMARY_COLOR};
                color: {ui_style.TEXT_COLOR};
                border: 2px solid {ui_style.PRIMARY_COLOR};
                border-radius: 8px;
                padding: 4px 12px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton#playerControlBtn:hover {{
                background-color: {ui_style.PRIMARY_HOVER};
                border: 2px solid {ui_style.PRIMARY_HOVER};
                padding: 4px 12px;
            }}
            QPushButton#playerControlBtn:pressed {{
                background-color: {ui_style.PRIMARY_ACTIVE};
                border: 2px solid {ui_style.PRIMARY_ACTIVE};
                padding: 4px 12px;
            }}
            QPushButton#playerControlBtn:focus {{
                outline: none;
                border: 2px solid {ui_style.PRIMARY_HOVER};
            }}
        """)
            nav_group.addWidget(self.play_pause_btn)

        # next_frame_btn removido

        # Botão de tela cheia
        if not getattr(self, '_player_controls_locked', False):
            self.fullscreen_btn = SimpleAnimatedButton("⤢")
            self.fullscreen_btn.setObjectName("playerControlBtn")
            self.fullscreen_btn.setToolTip("Tela cheia")
            self.fullscreen_btn.clicked.connect(self._toggle_fullscreen)
            self.fullscreen_btn.setFixedHeight(36)
            self.fullscreen_btn.setFixedWidth(48)
            self.fullscreen_btn.setStyleSheet(f"""
            QPushButton#playerControlBtn {{
                background-color: {ui_style.PRIMARY_COLOR};
                color: {ui_style.TEXT_COLOR};
                border: 2px solid {ui_style.PRIMARY_COLOR};
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 14px;
                font-weight: 600;
            }}
            QPushButton#playerControlBtn:hover {{
                background-color: {ui_style.PRIMARY_HOVER};
                border: 2px solid {ui_style.PRIMARY_HOVER};
                padding: 4px 8px;
            }}
            QPushButton#playerControlBtn:pressed {{
                background-color: {ui_style.PRIMARY_ACTIVE};
                border: 2px solid {ui_style.PRIMARY_ACTIVE};
                padding: 4px 8px;
            }}
            QPushButton#playerControlBtn:focus {{
                outline: none;
                border: 2px solid {ui_style.PRIMARY_HOVER};
            }}
        """)
            nav_group.addWidget(self.fullscreen_btn)

        if not getattr(self, '_player_controls_locked', False):
            pc_row.addLayout(nav_group)
            pc_row.addSpacing(12)

        # Grupo de velocidade
        if not getattr(self, '_player_controls_locked', False):
            speed_group = QHBoxLayout()
            speed_group.setSpacing(6)
            speed_group.setContentsMargins(0, 0, 0, 0)
            speed_label = QLabel("VEL:")
            speed_label.setStyleSheet(f"color: {ui_style.TEXT_COLOR}; font-weight: 600;")
            speed_group.addWidget(speed_label)
            self.speed_combo = QComboBox()
            self.speed_combo.addItems(["0.25x", "0.5x", "1x", "1.5x", "2x"])
            self.speed_combo.setCurrentText("1x")
            self.speed_combo.currentTextChanged.connect(self._change_speed)
            self.speed_combo.setFixedHeight(32)
            self.speed_combo.setStyleSheet(f"color: {ui_style.TEXT_COLOR};")
            speed_group.addWidget(self.speed_combo)
            pc_row.addLayout(speed_group)
            pc_row.addSpacing(12)

        # Grupo de informações e anotação
        if not getattr(self, '_player_controls_locked', False):
            info_group = QHBoxLayout()
            info_group.setSpacing(6)
            info_group.setContentsMargins(0, 0, 0, 0)
            self.frame_info_label = QLabel("Frame: 0/0")
            self.frame_info_label.setStyleSheet(f"color: {ui_style.TEXT_COLOR}; font-weight: 600;")
            info_group.addWidget(self.frame_info_label)
            # annotate_btn removido

            pc_row.addLayout(info_group)

        pc_vbox.addLayout(pc_row)
        # Posiciona a barra do player abaixo do vídeo, no espaço dedicado
        left_layout.addWidget(player_controls, alignment=Qt.AlignHCenter)
        try:
            left_layout.addSpacing(8)
        except Exception:
            pass
        # Garante uma altura mínima confortável para a barra do player
        try:
            self._update_player_min_height()
        except Exception:
            pass

        # Reforça bloqueio permanente (oculta, desativa e desconecta) quando travado
        if getattr(self, '_player_controls_locked', False):
            try:
                self._disable_player_controls_permanently()
            except Exception:
                pass
        # Define largura fixa inicial para a barra do player (quando não estiver travada)
        if not getattr(self, '_player_controls_locked', False):
            try:
                self._update_player_controls_width()
            except Exception:
                pass
        # Centraliza horizontalmente o frame do vídeo
        left_layout.addWidget(self.video_frame, alignment=Qt.AlignHCenter)

        # Botões inferiores com responsividade (horizontal ou grid)
        self.controls_widget = QWidget()
        # Desvincula a largura dos botões da largura do vídeo
        self.controls_widget.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Cria botões com tamanho consistente
        self.btn_video = SimpleAnimatedButton("Anexar Vídeo")
        self.btn_video.setFixedHeight(40)
        self.btn_video.setMinimumWidth(160)
        self.btn_video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_video.setToolTip("Anexar Vídeo")
        self.btn_video.clicked.connect(self._load_video)

        self.btn_camera = SimpleAnimatedButton("Câmera")
        self.btn_camera.setFixedHeight(40)
        self.btn_camera.setMinimumWidth(160)
        self.btn_camera.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_camera.setToolTip("Câmera")
        self.btn_camera.clicked.connect(self._start_camera)

        self.reset_btn = SimpleAnimatedButton("Resetar")
        self.reset_btn.setFixedHeight(40)
        self.reset_btn.setMinimumWidth(160)
        self.reset_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.reset_btn.setToolTip("Resetar seleção e estado")
        self.reset_btn.clicked.connect(self._reset_selection)

        # save_btn removido; salvamento apenas pelo painel do juiz

        # Constrói layout inicial como horizontal e registra modo
        self._rebuild_controls_layout('horizontal')
        # Centraliza inicialmente sob o vídeo; depois será convertido para posicionamento absoluto
        left_layout.addWidget(self.controls_widget, alignment=Qt.AlignHCenter)
        main_layout.addWidget(left_widget)

        # ===== LADO DIREITO =====
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        # Guarda referência para ajuste responsivo de largura
        self.right_scroll = right_scroll
        right_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        right_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(10)
        right_layout.setContentsMargins(8, 8, 8, 8)

        # Tabs no painel direito
        tab_widget = QTabWidget()
        tab_widget.setObjectName("analysisTabs")

        # Status
        status_frame = QFrame()
        status_frame.setObjectName("sectionCard")
        status_layout = QVBoxLayout(status_frame)
        self.status_label = QLabel(
            "Aguardando análise...\nClique em uma pessoa para analisar")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet(f"""
            color: {COLOR_NEUTRAL}; 
            font-size: 12px; 
            padding: 10px; 
            background-color: {ui_style.SURFACE_COLOR};
            border-radius: 6px;
            border-left: 4px solid {ui_style.PRIMARY_COLOR};
            min-height: 80px;
        """)
        self.status_label.setWordWrap(True)
        status_layout.addWidget(self.status_label)

        # Informações da pessoa selecionada
        selection_frame = QFrame()
        selection_frame.setObjectName("sectionCard")
        selection_layout = QVBoxLayout(selection_frame)
        self.selection_label = QLabel("Nenhuma pessoa selecionada")
        self.selection_label.setStyleSheet(f"""
            color: {ui_style.PRIMARY_COLOR};
            font-size: 13px;
            font-weight: bold;
            padding: 8px;
            background-color: {ui_style.SURFACE_COLOR};
            border-radius: 5px;
            text-align: center;
            min-height: 20px;
        """)
        self.selection_label.setAlignment(Qt.AlignCenter)
        selection_layout.addWidget(self.selection_label)
        right_layout.addWidget(selection_frame)

        # Contador de repetições
        rep_frame = QFrame()
        rep_frame.setObjectName("sectionCard")
        rep_layout = QVBoxLayout(rep_frame)
        try:
            rep_layout.setContentsMargins(8, 8, 8, 8)
        except Exception:
            pass
        self.rep_label = QLabel("Repetições: 0")
        self.rep_label.setStyleSheet(f"""
            color: {ui_style.PRIMARY_COLOR};
            font-size: 14px;
            font-weight: bold;
            padding: 10px;
            background-color: {ui_style.SURFACE_COLOR};
            border-radius: 5px;
            text-align: center;
            min-height: 20px;
        """)
        self.rep_label.setAlignment(Qt.AlignCenter)
        rep_layout.addWidget(self.rep_label)
        try:
            rep_frame.setFixedHeight(56)
        except Exception:
            pass
        left_layout.addWidget(rep_frame)

        # Ângulos
        angles_frame = QFrame()
        angles_frame.setObjectName("sectionCard")
        angles_layout = QVBoxLayout(angles_frame)
        angles_title = QLabel("ÂNGULOS:")
        angles_title.setObjectName("sectionTitle")
        angles_title.setAlignment(Qt.AlignLeft)
        angles_layout.addWidget(angles_title)
        self.angle_labels = {}
        angle_config = [
            ('knee_angle', 'Ângulo do Joelho'),
            ('hip_angle', 'Ângulo do Quadril'),
            ('torso_angle', 'Ângulo do Tronco'),
            ('back_angle', 'Ângulo das Costas')
        ]

        for name, display_name in angle_config:
            lbl = QLabel(f"{display_name}: --°")
            lbl.setStyleSheet("""
                padding: 6px; 
                background-color: rgba(255,255,255,0.03); 
                border-radius: 4px; 
                margin: 1px;
                font-size: 12px;
                min-height: 18px;
            """)
            self.angle_labels[name] = lbl
            angles_layout.addWidget(lbl)

        # Pequeno gráfico de variação dos ângulos
        if HAS_PYQTGRAPH and SHOW_ANGLE_PLOT:
            self.angle_plot = pg.PlotWidget()
            self.angle_plot.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Fixed)
            self.angle_plot.setMinimumHeight(120)
            self.angle_plot.setMaximumHeight(180)
            self.angle_plot.setBackground(ui_style.SURFACE_COLOR)
            try:
                # Reduzir padding interno para aproveitar melhor o espaço
                self.angle_plot.getPlotItem().getViewBox().setPadding(0.02)
                # Ocultar grade por padrão para visual mais limpo
                self.angle_plot.showGrid(x=False, y=False)
            except Exception:
                pass
            # Legenda compacta
            try:
                self.angle_plot.addLegend(offset=(10, 10))
            except Exception:
                self.angle_plot.addLegend()
            # Linhas mais finas para visual compacto
            self.knee_curve = self.angle_plot.plot(
                pen=pg.mkPen('#1BC0FF', width=1), name='Joelho')
            self.hip_curve = self.angle_plot.plot(
                pen=pg.mkPen('#28A745', width=1), name='Quadril')
            self.torso_curve = self.angle_plot.plot(
                pen=pg.mkPen('#DC3545', width=1), name='Tronco')

        # Tab de Análise Biomecânica
        analysis_tab = QWidget()
        analysis_tab_layout = QVBoxLayout(analysis_tab)
        analysis_tab_layout.setContentsMargins(0, 0, 0, 0)
        analysis_tab_layout.addWidget(status_frame)
        analysis_tab_layout.addWidget(angles_frame)
        if HAS_PYQTGRAPH and SHOW_ANGLE_PLOT:
            analysis_tab_layout.addWidget(self.angle_plot)
        tab_widget.addTab(analysis_tab, "Análise Biomecânica")

        # Avaliação manual
        judge_frame = QFrame()
        judge_frame.setObjectName("sectionCard")
        judge_layout = QVBoxLayout(judge_frame)
        judge_title = QLabel("AVALIAÇÃO / JULGAMENTO:")
        judge_title.setObjectName("sectionTitle")
        judge_title.setAlignment(Qt.AlignLeft)
        judge_layout.addWidget(judge_title)

        judge_buttons_layout = QHBoxLayout()
        judge_buttons = [
            ("VÁLIDO", COLOR_VALID, True, "btn_valido"),
            ("INVÁLIDO", COLOR_INVALID, False, "btn_invalido")
        ]

        for text, color, valid, obj_name in judge_buttons:
            btn = SimpleAnimatedButton(text)
            btn.setObjectName(obj_name)
            btn.setStyleSheet(f"""
                background-color: {color}; 
                color: white; 
                font-weight: bold; 
                padding: 8px;
                border-radius: 5px;
                font-size: 12px;
                min-height: 35px;
            """)
            btn.clicked.connect(
                lambda checked, v=valid: self._manual_judgment(v))
            judge_buttons_layout.addWidget(btn)

        judge_layout.addLayout(judge_buttons_layout)

        # Observações do juiz
        self.judge_notes = QTextEdit()
        self.judge_notes.setPlaceholderText("Observações do juiz...")
        self.judge_notes.setMinimumHeight(72)
        judge_layout.addWidget(self.judge_notes)

        # Status combinado IA + Juiz
        self.combined_status_label = QLabel("IA: Pendente | Juiz: Pendente")
        self.combined_status_label.setAlignment(Qt.AlignCenter)
        self.combined_status_label.setStyleSheet(f"""
            color: {ui_style.PRIMARY_COLOR};
            font-size: 13px;
            font-weight: bold;
            padding: 8px;
            background-color: {ui_style.SURFACE_COLOR};
            border-radius: 6px;
        """)
        judge_layout.addWidget(self.combined_status_label)

        # Painel informativo do juiz: resumo da análise atual
        self.judge_info_label = QLabel(
            "Sem dados atuais.\nVá à aba Análise e inicie a leitura.")
        self.judge_info_label.setWordWrap(True)
        self.judge_info_label.setStyleSheet(f"""
            color: {ui_style.MUTED_COLOR};
            font-size: 12px;
            padding: 10px;
            background-color: {ui_style.SURFACE_COLOR};
            border-radius: 6px;
            border-left: 4px solid {ui_style.PRIMARY_COLOR};
            min-height: 48px;
        """)
        judge_layout.addWidget(self.judge_info_label)

        self.judge_save_btn = SimpleAnimatedButton("Salvar Tentativa")
        self.judge_save_btn.setToolTip("Salvar a tentativa atual no banco")
        self.judge_save_btn.setFixedHeight(24)
        self.judge_save_btn.setMinimumWidth(128)
        self.judge_save_btn.setStyleSheet(f"""
            background-color: {ui_style.PRIMARY_COLOR};
            color: {ui_style.TEXT_COLOR};
            font-weight: 600;
            padding: 3px 10px;
            border-radius: 5px;
            font-size: 12px;
        """)
        self.judge_save_btn.clicked.connect(self._salvar_tentativa)
        try:
            self.judge_save_btn.setEnabled(False)
        except Exception:
            pass
        judge_layout.addWidget(self.judge_save_btn, alignment=Qt.AlignHCenter)

        judge_tab = QWidget()
        judge_tab_layout = QVBoxLayout(judge_tab)
        judge_tab_layout.setContentsMargins(0, 0, 0, 0)
        judge_tab_layout.addWidget(judge_frame)
        tab_widget.addTab(judge_tab, "Avaliação / Julgamento")

        # Configurações
        config_frame = QFrame()
        config_frame.setObjectName("sectionCard")
        config_layout = QVBoxLayout(config_frame)
        config_title = QLabel("CONFIGURAÇÕES:")
        config_title.setObjectName("sectionTitle")
        config_title.setAlignment(Qt.AlignLeft)
        config_layout.addWidget(config_title)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight)
        form_layout.setFormAlignment(Qt.AlignLeft)
        form_layout.setHorizontalSpacing(12)
        form_layout.setVerticalSpacing(10)
        # Atleta
        athlete_label = QLabel("Atleta:")
        self.athlete_combo = QComboBox()
        self.athlete_combo.setEditable(True)

        # Carrega lista inicial
        self.athlete_combo.addItems(["Clique para carregar atletas..."])
        self.athlete_combo.setCurrentIndex(0)

        # Conecta o clique para carregar a lista
        self.athlete_combo.mousePressEvent = self._load_athletes_on_click

        # Autocompletar baseado nos itens existentes
        completer = QCompleter()
        completer.setModel(self.athlete_combo.model())
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.athlete_combo.setCompleter(completer)

        try:
            self.athlete_combo.setStyleSheet(
                "QComboBox::drop-down { width: 0px; }\n"
                "QComboBox::down-arrow { image: none; }"
            )
        except Exception:
            pass

        self.athlete_combo.setToolTip("Clique para carregar lista de atletas do histórico")
        self.athlete_combo.setMinimumWidth(220)

        # Apenas o combo (sem botão adicional)
        form_layout.addRow(athlete_label, self.athlete_combo)

        # Exercício
        exercise_label = QLabel("Exercício:")
        self.exercise_combo = QComboBox()
        self.exercise_combo.addItems(
            ["Selecione...", "Agachamento", "Levantamento Terra"])
        self.exercise_combo.setCurrentIndex(0)
        self.exercise_combo.setToolTip("Selecione o exercício analisado")
        self.exercise_combo.setMinimumWidth(220)
        form_layout.addRow(exercise_label, self.exercise_combo)

        # Modelo por exercício (exibido automaticamente, sem seleção manual)
        model_label = QLabel("Modelo:")
        self.model_name_label = QLabel("Auto (por exercício)")
        self.model_name_label.setMinimumWidth(220)
        self.model_mode = 'auto'
        # Mapeamento completo entre exercícios e modelos
        self._exercise_model_map = {
            'agachamento': 'squat',
            'levantamento terra': 'deadlift'
        }
                
        def _on_exercise_change(_idx):
            try:
                # Determinar chave do exercício atual de forma robusta
                txt = (self.exercise_combo.currentText() or '').strip().lower()
                ex_key = self._exercise_model_map.get(txt)
                if ex_key in ('squat', 'deadlift'):
                    # Verifica se o modelo especializado existe
                    base = models_dir()
                    spec_path = os.path.join(base, f"model_{ex_key}.pkl")
                    if os.path.exists(spec_path):
                        # Alterna para modo automático por exercício
                        self._switch_model_mode('auto')
                    else:
                        # Fallback para modelo geral
                        self._switch_model_mode('default')
                        try:
                            self.status_label.setText(
                                "Modelo especializado não encontrado; usando modelo geral.")
                        except Exception:
                            pass
                else:
                    # Exercício não mapeado: usar modelo geral
                    self._switch_model_mode('default')
            except Exception:
                pass
        try:
            self.exercise_combo.currentIndexChanged.connect(_on_exercise_change)
        except Exception:
            pass
        form_layout.addRow(model_label, self.model_name_label)

        # Tentativa
        attempt_label = QLabel("Tentativa:")
        self.attempt_spin = QSpinBox()
        self.attempt_spin.setRange(1, 3)
        self.attempt_spin.setValue(1)
        self.attempt_spin.setAlignment(Qt.AlignCenter)
        self.attempt_spin.setToolTip("Número da tentativa (1–3)")
        self.attempt_spin.setFixedWidth(70)
        # Esconde setas para visual minimalista
        try:
            self.attempt_spin.setButtonSymbols(QAbstractSpinBox.NoButtons)
        except Exception:
            pass
        form_layout.addRow(attempt_label, self.attempt_spin)

        config_layout.addLayout(form_layout)

        right_layout.addWidget(config_frame)

        # Histórico
        history_frame = QFrame()
        history_frame.setObjectName("sectionCard")
        history_layout = QVBoxLayout(history_frame)
        history_title = QLabel("HISTÓRICO DE TENTATIVAS:")
        history_title.setObjectName("sectionTitle")
        history_title.setAlignment(Qt.AlignLeft)
        history_layout.addWidget(history_title)
        self.history_tree = QTreeWidget()
        self.history_tree.setHeaderLabels(
            ["Atleta", "Exercício", "Tent.", "Auto", "Juiz", "Hora"])
        self.history_tree.setMinimumHeight(120)
        self.history_tree.setStyleSheet("font-size: 11px;")

        # Ajustar largura das colunas
        self.history_tree.setColumnWidth(0, 70)   # Atleta
        self.history_tree.setColumnWidth(1, 90)   # Exercício
        self.history_tree.setColumnWidth(2, 45)   # Tentativa
        self.history_tree.setColumnWidth(3, 40)   # Auto
        self.history_tree.setColumnWidth(4, 40)   # Juiz
        self.history_tree.setColumnWidth(5, 65)   # Hora

        history_layout.addWidget(self.history_tree)

        # Botões de exportação/limpeza
        history_btns = QWidget()
        history_btns_layout = QHBoxLayout(history_btns)
        history_btns_layout.setContentsMargins(0, 0, 0, 0)
        refresh_btn = SimpleAnimatedButton("Atualizar")
        refresh_btn.clicked.connect(self._refresh_history_from_db)
        export_csv_btn = SimpleAnimatedButton("Exportar CSV")
        export_csv_btn.clicked.connect(self._export_history_to_csv)
        export_pdf_btn = SimpleAnimatedButton("Exportar PDF")
        export_pdf_btn.clicked.connect(self._export_history_to_pdf)
        clear_btn = SimpleAnimatedButton("Limpar histórico")
        clear_btn.clicked.connect(self._clear_history)
        for b in (refresh_btn, export_csv_btn, export_pdf_btn, clear_btn):
            history_btns_layout.addWidget(b)
        history_layout.addWidget(history_btns)

        history_tab = QWidget()
        history_tab_layout = QVBoxLayout(history_tab)
        history_tab_layout.setContentsMargins(0, 0, 0, 0)
        history_tab_layout.addWidget(history_frame)
        tab_widget.addTab(history_tab, "Histórico")

        # Espaço flexível no final
        right_layout.addWidget(tab_widget)
        right_layout.addStretch()

        right_scroll.setWidget(right_widget)
        main_layout.addWidget(right_scroll)
        try:
            main_layout.setStretch(0, 3)
            main_layout.setStretch(1, 2)
        except Exception:
            pass
        # Define largura inicial responsiva do painel direito
        try:
            self._update_right_panel_width()
        except Exception:
            pass

        try:
            self.analysisUpdated.connect(lambda _p: self._update_save_button_state())
            self.athlete_combo.currentTextChanged.connect(self._update_save_button_state)
            self.exercise_combo.currentIndexChanged.connect(self._update_save_button_state)
            self.judge_notes.textChanged.connect(self._update_save_button_state)
        except Exception:
            pass

    # ===== MÉTODOS DE ANÁLISE =====
    def _get_landmark_name(self, index: int) -> str:
        landmark_names = {
            0: "NOSE", 7: "LEFT_EAR", 8: "RIGHT_EAR",
            11: "LEFT_SHOULDER", 12: "RIGHT_SHOULDER",
            23: "LEFT_HIP", 24: "RIGHT_HIP",
            25: "LEFT_KNEE", 26: "RIGHT_KNEE",
            27: "LEFT_ANKLE", 28: "RIGHT_ANKLE",
        }
        return landmark_names.get(index, f"UNKNOWN_{index}")

    def _calculate_stability(self, angles: dict) -> float:
        """Calcula uma métrica de estabilidade normalizada (0..1).
        Normaliza variações de ângulo por 180° para compatibilizar com os
        limiares do sistema de pontuação, evitando penalização excessiva
        durante o movimento dinâmico.
        """
        if not self.previous_angles:
            self.previous_angles = angles.copy()
            return 0.0

        total_diff = 0.0
        count = 0
        for key, curr_val in angles.items():
            if key in self.previous_angles:
                prev_val = float(self.previous_angles[key])
                diff = abs(float(curr_val) - prev_val)
                # Normaliza diffs de ângulo para 0..1 (graus / 180)
                if ('angle' in key) or key.endswith('_angle'):
                    diff_norm = diff / 180.0
                else:
                    # Para métricas não angulares (ex.: simetria já em graus),
                    # mantém como está ou considere uma normalização leve no futuro
                    diff_norm = diff / 180.0 if 'symmetry' in key else diff
                total_diff += diff_norm
                count += 1

        # Atualiza referência para próxima iteração
        self.previous_angles = angles.copy()
        return total_diff / max(count, 1)

    def _apply_smoothing(self, angles: dict) -> dict:
        """Aplica suavização exponencial simples (EMA) aos ângulos."""
        if not angles:
            return angles
        alpha = getattr(self, 'smoothing_alpha', 0.3)
        if not self.smoothed_angles:
            # Inicializa com primeiros valores
            self.smoothed_angles = angles.copy()
            return self.smoothed_angles.copy()
        smoothed = {}
        for k, v in angles.items():
            prev = self.smoothed_angles.get(k, v)
            smoothed_val = alpha * float(v) + (1 - alpha) * float(prev)
            smoothed[k] = smoothed_val
        self.smoothed_angles = smoothed.copy()
        return smoothed

    def _update_background_pixmap(self):
        if hasattr(self, '_bg_pixmap') and self._bg_pixmap and not self._bg_pixmap.isNull():
            scaled = self._bg_pixmap.scaled(
                self.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            self._bg_label.setPixmap(scaled)
            self._bg_label.setGeometry(self.rect())

    def resizeEvent(self, event):
        # Unifica atualização de fundo, painel direito e área de vídeo
        super().resizeEvent(event)
        try:
            self._update_background_pixmap()
        except Exception:
            pass
        try:
            self._update_right_panel_width()
        except Exception:
            pass
        self._resize_video_area()
        # Atualiza layout dos botões inferiores conforme largura disponível
        try:
            self._update_bottom_controls_layout()
        except Exception:
            pass

    def _format_evaluation_text(self, evaluation_obj, angles: dict | None = None, exercise: str | None = None) -> str:
        """Formata texto unificado de avaliação para exibição no status_label.
        Suporta avaliação básica (dict) e detalhada (objeto DetailedEvaluation).
        """
        try:
            # Detecta tipo
            is_dict = isinstance(evaluation_obj, dict)
            lines = []
            header = "🏆 Avaliação IPF"
            if exercise:
                header += f" – {exercise}"
            lines.append(header)
            lines.append("")

            # Resultado simplificado: Movimento Correto/Incorrreto
            try:
                if is_dict:
                    is_valid = bool(evaluation_obj.get('valid'))
                else:
                    perc = getattr(evaluation_obj, 'percentage', None)
                    is_valid = (perc is not None and float(perc) >= 60)
                emoji = "✅" if is_valid else "❌"
                lines.append(f"Resultado: {emoji} {'Movimento Correto' if is_valid else 'Movimento Incorreto'}")
                lines.append("")
            except Exception:
                pass

            # Luzes
            lights = []
            if is_dict:
                lights = evaluation_obj.get('lights', []) or []
            else:
                lights = list(getattr(evaluation_obj, 'ipf_lights', []) or [])
            if lights:
                lights_display = ", ".join(
                    "Branca" if l == 'white' else "Vermelha" for l in lights)
                lines.append(f"Luzes: {lights_display}")

            # Pontuação / Percentual
            if is_dict and 'score' in evaluation_obj and 'max_score' in evaluation_obj:
                score = evaluation_obj.get('score')
                max_score = evaluation_obj.get('max_score')
                quality = evaluation_obj.get('quality')
                if score is not None and max_score is not None:
                    lines.append(f"Pontuação: {score}/{max_score}")
                if quality is not None:
                    lines.append(f"Qualidade: {quality}")
            else:
                perc = getattr(evaluation_obj, 'percentage', None)
                level = getattr(
                    getattr(evaluation_obj, 'level', None), 'value', None)
                mqi = getattr(evaluation_obj, 'movement_quality_index', None)
                if perc is not None:
                    lines.append(f"Percentual: {float(perc):.1f}%")
                if level is not None:
                    lines.append(f"Nível: {level}")
                if mqi is not None:
                    lines.append(f"Índice de Qualidade: {float(mqi):.1f}/100")

            # Critérios (detalhada)
            criteria = getattr(evaluation_obj, 'criteria_scores', None)
            if criteria:
                lines.append("")
                lines.append("📋 Critérios:")
                for crit in criteria:
                    try:
                        status = "✓" if getattr(crit, 'passed', False) else "✗"
                        raw_name = str(getattr(crit, 'name', '')).replace('_', ' ').strip()
                        map_pt = {
                            'depth': 'Profundidade',
                            'stability': 'Estabilidade',
                            'torso position': 'Posição do Tronco',
                            'symmetry': 'Simetria',
                        }
                        name = map_pt.get(raw_name.lower(), raw_name.title())
                        score = float(getattr(crit, 'score', 0))
                        max_score = float(getattr(crit, 'max_score', 0))
                        lines.append(
                            f"{status} {name}: {score:.1f}/{max_score:.1f}")
                    except Exception:
                        continue

            # Feedback geral
            feedback_items = []
            if is_dict:
                feedback_items = list(evaluation_obj.get('feedback', []) or [])
            else:
                feedback_items = list(
                    getattr(evaluation_obj, 'overall_feedback', []) or [])
            # Remove quaisquer menções a 'modelo treinado' do feedback
            try:
                feedback_items = [
                    f for f in feedback_items
                    if 'modelo treinado' not in str(f).lower()
                ]
            except Exception:
                pass
            if feedback_items:
                lines.append("")
                lines.append("💬 Feedback:")
                for item in feedback_items[:3]:
                    lines.append(f"• {item}")


            # Ângulos
            if angles:
                angle_names = {
                    'knee_angle': 'Joelho', 'hip_angle': 'Quadril',
                    'torso_angle': 'Tronco', 'back_angle': 'Costas'
                }
                parts = []
                for key in ('knee_angle', 'hip_angle', 'torso_angle', 'back_angle'):
                    if key in angles:
                        try:
                            parts.append(
                                f"{angle_names[key]}: {float(angles[key]):.1f}°")
                        except Exception:
                            parts.append(f"{angle_names[key]}: --°")
                if parts:
                    lines.append("")
                    lines.append("Ângulos:")
                    lines.append("\n".join(parts))

            # Métricas da última repetição (se disponíveis)
            try:
                if getattr(self, 'current_rep_data', None) and len(self.current_rep_data) > 0:
                    last_metrics = self.current_rep_data[-1].get('metrics')
                    if last_metrics:
                        lines.append("")
                        lines.append("⏱ Métricas da última repetição:")
                        tut = float(last_metrics.get('time_under_tension', 0))
                        vel = float(last_metrics.get('velocity', 0))
                        phases = last_metrics.get('phases', {}) or {}
                        bar = last_metrics.get('bar_path', {}) or {}
                        lines.append(
                            f"• TUT: {tut:.2f}s | Veloc.: {vel:.2f}°/s")
                        lines.append(
                            f"• Fases – Excêntrica: {float(phases.get('eccentric', 0)):.2f}s, Concêntrica: {float(phases.get('concentric', 0)):.2f}s")
                        if bar:
                            lines.append(
                                f"• Trajetória da barra – Percurso: {float(bar.get('length', 0)):.1f}px, Retidão: {float(bar.get('straightness', 1)):.2f}")
                        risk = last_metrics.get('risk_flags') or []
                        if risk:
                            display = ", ".join(
                                r.replace('_', ' ').capitalize() for r in risk[:4])
                            lines.append(f"⚠ Alertas: {display}")
            except Exception:
                pass
            
            return "\n".join(lines)
        except Exception as e:
            return f"Falha ao formatar avaliação: {e}"

    def _display_ipf_feedback(self, evaluation: dict, angles: dict, exercise: str):
        # Debug detalhado de avaliação para investigação
        try:
            print(f"[DEBUG] Avaliação {exercise}: valid={evaluation.get('valid')}, score={evaluation.get('score')}, lights={evaluation.get('lights')}, feedback={evaluation.get('feedback')}, quality={evaluation.get('quality')}")
        except Exception:
            pass
        # Texto unificado
        self.status_label.setText(self._format_evaluation_text(
            evaluation, angles=angles, exercise=exercise))
        # Atualiza resultado automático para status combinado
        self.auto_result = "Válido" if evaluation.get('valid') else "Inválido"
        self._update_combined_status(angles)
        # Armazena resumo para o painel do juiz
        try:
            self.last_eval_summary = {
                'type': 'ipf_basic',
                'valid': bool(evaluation.get('valid')),
                'score': evaluation.get('score'),
                'max_score': evaluation.get('max_score'),
                'lights': evaluation.get('lights', [])
            }
        except Exception:
            self.last_eval_summary = None
        self._update_judge_info_panel()

        if evaluation['valid']:
            self.status_label.setStyleSheet(f"""
                color: {COLOR_VALID}; 
                font-weight: bold; 
                background-color: rgba(76, 175, 80, 0.1); 
                padding: 10px; 
                border-radius: 6px;
                border-left: 4px solid {COLOR_VALID};
                min-height: 80px;
            """)
        else:
            self.status_label.setStyleSheet(f"""
                color: {COLOR_INVALID}; 
                font-weight: bold; 
                background-color: rgba(244, 67, 54, 0.1); 
                padding: 10px; 
                border-radius: 6px;
                border-left: 4px solid {COLOR_INVALID};
                min-height: 80px;
            """)

    def _display_enhanced_feedback(self, evaluation):
        """Exibe feedback usando formato unificado para avaliação detalhada"""
        if not evaluation:
            return
        self.status_label.setText(self._format_evaluation_text(evaluation))
        # Atualiza resultado automático
        self.auto_result = "Válido" if evaluation.percentage >= 60 else "Inválido"
        self._update_combined_status()
        # Armazena resumo para o painel do juiz
        try:
            self.last_eval_summary = {
                'type': 'ipf_enhanced',
                'percentage': float(evaluation.percentage),
                'level': str(evaluation.level.value),
                'ipf_lights': list(evaluation.ipf_lights)
            }
        except Exception:
            self.last_eval_summary = None
        self._update_judge_info_panel()

        # Cores baseadas na porcentagem
        if evaluation.percentage >= 80:
            color = COLOR_VALID
            bg_color = "rgba(76, 175, 80, 0.1)"
        elif evaluation.percentage >= 60:
            color = "#f39c12"
            bg_color = "rgba(243, 156, 18, 0.1)"
        else:
            color = COLOR_INVALID
            bg_color = "rgba(244, 67, 54, 0.1)"

        self.status_label.setStyleSheet(f"""
            color: {color}; 
            font-weight: bold; 
            background-color: {bg_color}; 
            padding: 10px; 
            border-radius: 6px;
            border-left: 4px solid {color};
            min-height: 80px;
        """)

    def _export_evaluation_report(self, evaluation):
        """Exporta relatório detalhado da avaliação"""
        try:
            from PyQt5.QtWidgets import QFileDialog, QMessageBox
            import json
            import time

            # Solicita local para salvar
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "Salvar Relatório de Avaliação",
                f"relatorio_avaliacao_{int(time.time())}.json",
                "JSON Files (*.json);;Text Files (*.txt)"
            )

            if not filename:
                return

            # Prepara dados para exportação
            report_data = {
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "athlete": self.athlete_combo.currentText(),
                "exercise": self.exercise_combo.currentText(),
                "attempt": self.attempt_spin.value(),
                "percentage": evaluation.percentage,
                "level": evaluation.level.value,
                "movement_quality_index": evaluation.movement_quality_index,
                "ipf_lights": evaluation.ipf_lights,
                "criteria_scores": [
                    {
                        "name": c.name,
                        "score": c.score,
                        "max_score": c.max_score,
                        "weight": c.weight,
                        "passed": c.passed,
                        "feedback": c.feedback
                    } for c in evaluation.criteria_scores
                ],
                "overall_feedback": evaluation.overall_feedback,
                "recommendations": evaluation.recommendations
            }

            # Salva arquivo
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(
                self,
                "Relatório Exportado",
                f"Relatório salvo com sucesso em:\n{filename}"
            )

        except Exception as e:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Erro na Exportação",
                f"Erro ao exportar relatório:\n{str(e)}"
            )

    def _detect_rep_cycle(self, angles: dict, evaluation: dict, exercise: str):
        knee_angle = angles.get('knee_angle', 180)

        exercise_map = {"Agachamento": "squat",
                        "Levantamento Terra": "deadlift"}
        exercise_key = exercise_map.get(exercise, "squat")

        if exercise_key == "squat":
            start_threshold, end_threshold = 140, 160
        elif exercise_key == "deadlift":
            start_threshold, end_threshold = 150, 170
        else:
            start_threshold, end_threshold = 140, 160

        # Acumula stream por frame para métricas da repetição
        now_ts = time.time()
        try:
            if getattr(self, 'rep_start_time', None) is not None:
                if not hasattr(self, 'current_rep_stream'):
                    self.current_rep_stream = []
                self.current_rep_stream.append({
                    't': now_ts,
                    'knee': knee_angle,
                    'back': angles.get('back_angle', None)
                })
        except Exception:
            pass

        # Atualiza contadores de histerese
        if knee_angle < start_threshold:
            self.rep_start_confirm += 1
        else:
            # perde a condição de início
            self.rep_start_confirm = 0

        if self.rep_start_time is not None and knee_angle > end_threshold:
            self.rep_end_confirm += 1
        else:
            # perde a condição de fim
            self.rep_end_confirm = 0

        # Confirma início quando atingir N frames consecutivos abaixo do limiar
        if self.rep_start_time is None and self.rep_start_confirm >= self.rep_confirm_frames_start:
            self.rep_start_time = time.time()
            self.current_rep_data = []
            self.current_rep_stream = []
            # zera contadores ao iniciar
            self.rep_start_confirm = 0
            self.rep_end_confirm = 0
            print(f"Inicio da repetição - Joelho: {knee_angle:.1f}°")

        # Confirma fim quando atingir N frames consecutivos acima do limiar
        elif self.rep_start_time is not None and self.rep_end_confirm >= self.rep_confirm_frames_end:
            rep_end = time.time()
            rep_duration = rep_end - self.rep_start_time
            print(f"Fim da repetição - Duração: {rep_duration:.2f}s")

            if rep_duration > 0.5:
                self.rep_count += 1
                self.rep_label.setText(f"Repetições: {self.rep_count}")

                # Métricas por repetição
                phases = self._compute_rep_phases(
                    getattr(self, 'current_rep_stream', []))
                avg_vel = self._compute_rep_velocity(
                    getattr(self, 'current_rep_stream', []))
                bar_metrics = self._bar_path_metrics_over_window(
                    self.bar_path_points)
                # Determina validade da repetição independente do tipo de 'evaluation'
                risk_flags = []
                try:
                    # Sinalizador de curvatura lombar excessiva
                    back_angle_val = angles.get('back_angle', 0) or 0
                    if back_angle_val > 30:
                        risk_flags.append('curvatura_lombar_elevada')

                    # Converte avaliação detalhada em validade simples
                    if isinstance(evaluation, dict):
                        is_valid = bool(evaluation.get('valid', True))
                    else:
                        lights = list(getattr(evaluation, 'ipf_lights', []) or [])
                        is_valid = (lights.count('white') >= 2)
                        if getattr(evaluation, 'percentage', 100) < 60:
                            risk_flags.append('qualidade_baixa')
                except Exception:
                    is_valid = True

                rep_data = {
                    'duration': rep_duration,
                    'angles': angles.copy(),
                    'evaluation': evaluation,
                    'timestamp': rep_end,
                    'valid': is_valid,
                    'exercise': exercise,
                    'metrics': {
                        'time_under_tension': rep_duration,
                        'velocity': avg_vel,
                        'phases': phases,
                        'bar_path': bar_metrics,
                        'risk_flags': risk_flags
                    }
                }
                self.current_rep_data.append(rep_data)
                self._add_to_history(rep_data)

                # Ativa overlay de luzes ao finalizar a repetição
                try:
                    if isinstance(evaluation, dict):
                        lights = evaluation.get('lights', []) or []
                    else:
                        lights = list(getattr(evaluation, 'ipf_lights', []) or [])
                    if lights:
                        self._activate_ipf_overlay(lights)
                except Exception:
                    pass

            self.rep_start_time = None
            self.current_rep_stream = []
            # zera contadores ao finalizar
            self.rep_start_confirm = 0
            self.rep_end_confirm = 0

    def _add_to_history(self, rep_data: dict):
        athlete = self.athlete_combo.currentText() or "Atleta"
        exercise = rep_data['exercise']
        attempt = self.attempt_spin.value()

        auto_text = "Aprovado" if rep_data['valid'] else "Reprovado"
        judge_text = "Pendente"

        item = QTreeWidgetItem([
            athlete,
            exercise,
            str(attempt),
            auto_text,
            judge_text,
            time.strftime("%H:%M:%S")
        ])
        self.history_tree.addTopLevelItem(item)

    def _refresh_history_from_db(self):
        try:
            self.history_tree.clear()
            # Tenta MSSQL via repositório avançado
            try:
                from db.analysis_repository import AnalysisRepository
                repo = AnalysisRepository()
                rows = list(repo.list(top=200))
                if rows:
                    for r in rows:
                        auto_text = "Aprovado" if bool(r.get('AUTO_VALIDO')) else "Reprovado"
                        judge_text = str(r.get('STATUS') or '') if r.get('STATUS') else "Pendente"
                        hora = ''
                        try:
                            dt = r.get('DATA_CRIACAO') or r.get('DATA_ATUALIZACAO')
                            hora = str(dt).split(' ')[1] if dt else ''
                        except Exception:
                            pass
                        item = QTreeWidgetItem([
                            str(r.get('ATLETA', '')),
                            str(r.get('EXERCICIO', '')),
                            str(r.get('TENTATIVA', 1)),
                            auto_text,
                            judge_text,
                            hora,
                        ])
                        self.history_tree.addTopLevelItem(item)
                    return
            except Exception:
                pass
            # Fallback MSSQL simples (db_connection)
            try:
                from db.db_connection import DatabaseConnection
                dbc = DatabaseConnection()
                rows = dbc.list_latest(top=200)
                if rows:
                    for r in rows:
                        auto_text = "Aprovado" if bool(r.get('AUTO_VALIDO')) else "Reprovado"
                        judge_text = str(r.get('STATUS') or '') if r.get('STATUS') else "Pendente"
                        hora = ''
                        try:
                            dt = r.get('DATA_CRIACAO') or r.get('DATA_ATUALIZACAO')
                            hora = str(dt).split(' ')[1] if dt else ''
                        except Exception:
                            pass
                        item = QTreeWidgetItem([
                            str(r.get('ATLETA', '')),
                            str(r.get('EXERCICIO', '')),
                            str(r.get('TENTATIVA', 1)),
                            auto_text,
                            judge_text,
                            hora,
                        ])
                        self.history_tree.addTopLevelItem(item)
                    return
            except Exception:
                pass
            # Fallback para SQLite local
            records = fetch_attempts(limit=200)
            for rec in records:
                auto_text = "Aprovado" if rec.get('auto_valid') else "Reprovado"
                judge_text = (
                    "Confirmado" if rec.get('judge_valid') else "Inválido"
                )
                hora = str(rec.get('created_at', ''))
                try:
                    hora = hora.split(' ')[1]
                except Exception:
                    pass
                item = QTreeWidgetItem([
                    str(rec.get('athlete', '')),
                    str(rec.get('exercise', '')),
                    str(rec.get('attempt', 1)),
                    auto_text,
                    judge_text,
                    hora,
                ])
                self.history_tree.addTopLevelItem(item)
        except Exception:
            pass

    def _manual_judgment(self, valid: bool):
        # Atualiza decisão do juiz e histórico
        self.last_judge_decision = "Confirmado" if valid else "Inválido"
        print(f"Juiz manual: {self.last_judge_decision}")
        self._update_combined_status()
        self._update_judge_info_panel()
        try:
            self._update_save_button_state()
        except Exception:
            pass
        if self.current_rep_data:
            top_item = self.history_tree.topLevelItem(
                self.history_tree.topLevelItemCount() - 1)
            if top_item:
                top_item.setText(4, "Confirmado" if valid else "Inválido")

    def _update_combined_status(self, angles: dict = None):
        ia = self.auto_result or "Pendente"
        juiz = self.last_judge_decision or "Pendente"
        angle_info = ""
        if angles and 'knee_angle' in angles:
            angle_info = f" (Joelho: {angles['knee_angle']:.0f}°)"
            self.last_angles = angles.copy()
        self.combined_status_label.setText(
            f"IA: {ia}{angle_info} | Juiz: {juiz}")
        # Atualiza gráfico
        if angles and HAS_PYQTGRAPH and SHOW_ANGLE_PLOT:
            self._update_angle_plot(angles)
        # Atualiza painel do juiz
        self._update_judge_info_panel()

    def _update_judge_info_panel(self):
        try:
            ia = self.auto_result or "Pendente"
            juiz = self.last_judge_decision or "Pendente"
            lines = [f"IA: {ia} | Juiz: {juiz}"]
            # Resumo de avaliação
            s = self.last_eval_summary
            if s:
                if s.get('type') == 'ipf_basic':
                    lights = s.get('lights', [])
                    lights_display = ", ".join(
                        "Branca" if l == 'white' else "Vermelha" for l in lights)
                    if s.get('score') is not None and s.get('max_score') is not None:
                        lines.append(
                            f"Pontuação IPF: {s.get('score')}/{s.get('max_score')}")
                    if lights:
                        lines.append(f"Luzes: {lights_display}")
                elif s.get('type') == 'ipf_enhanced':
                    lights = s.get('ipf_lights', [])
                    lights_display = ", ".join(
                        "Branca" if l == 'white' else "Vermelha" for l in lights)
                    if s.get('percentage') is not None and s.get('level') is not None:
                        lines.append(
                            f"Percentual: {s.get('percentage', 0):.1f}% | Nível: {s.get('level', '-')}")
                    if lights:
                        lines.append(f"Luzes: {lights_display}")
            # Últimos ângulos
            if self.last_angles:
                an = self.last_angles
                angle_names = {
                    'knee_angle': 'Joelho', 'hip_angle': 'Quadril',
                    'torso_angle': 'Tronco', 'back_angle': 'Costas'
                }
                angle_parts = []
                for key in ('knee_angle', 'hip_angle', 'torso_angle', 'back_angle'):
                    if key in an:
                        try:
                            angle_parts.append(
                                f"{angle_names[key]}: {float(an[key]):.0f}°")
                        except Exception:
                            angle_parts.append(f"{angle_names[key]}: --°")
                if angle_parts:
                    lines.append(" Ângulos: " + ", ".join(angle_parts))
            self.judge_info_label.setText("\n".join(lines))
        except Exception:
            pass

    def _update_angle_plot(self, angles: dict):
        try:
            for k in ('knee_angle', 'hip_angle', 'torso_angle'):
                if k in angles:
                    self.angle_series[k].append(float(angles[k]))
                    # Limita para 300 pontos
                    if len(self.angle_series[k]) > 300:
                        self.angle_series[k] = self.angle_series[k][-300:]
            x = list(range(len(self.angle_series['knee_angle'])))
            self.knee_curve.setData(x, self.angle_series['knee_angle'])
            self.hip_curve.setData(x, self.angle_series['hip_angle'])
            self.torso_curve.setData(x, self.angle_series['torso_angle'])
        except Exception:
            pass

    def _update_save_button_state(self):
        try:
            has_analysis = bool(getattr(self, 'last_analysis', None)) or bool(getattr(self, 'last_eval_summary', None))
            athlete_ok = bool((self.athlete_combo.currentText() or '').strip())
            exercise_ok = (self.exercise_combo.currentIndex() != 0)
            judge_decision = (self.last_judge_decision or '') in ("Confirmado", "Inválido")
            notes_ok = True
            if (self.last_judge_decision or '') == 'Inválido':
                notes_ok = bool((self.judge_notes.toPlainText() or '').strip())
            enabled = has_analysis and athlete_ok and exercise_ok and judge_decision and notes_ok
            if hasattr(self, 'judge_save_btn') and self.judge_save_btn:
                self.judge_save_btn.setEnabled(bool(enabled))
        except Exception:
            pass

    def _salvar_tentativa(self):
        try:
            if not self.current_rep_data and not self.last_eval_summary:
                QMessageBox.information(
                    self, "Sem dados", "Nenhuma avaliação disponível para salvar.")
                return
            # Validação de exercício selecionado
            if self.exercise_combo.currentIndex() == 0 or 'selecion' in self.exercise_combo.currentText().lower():
                QMessageBox.warning(self, "Exercício obrigatório",
                                    "Selecione um exercício antes de salvar a tentativa.")
                return
            # Validação de atleta
            if not (self.athlete_combo.currentText() or '').strip():
                QMessageBox.warning(self, "Atleta obrigatório",
                                    "Informe o nome do atleta antes de salvar.")
                return
            # Validação de decisão e notas do juiz
            juiz_status = self.last_judge_decision or "Pendente"
            notas_juiz = (self.judge_notes.toPlainText() if hasattr(self, 'judge_notes') else '').strip()
            if juiz_status == "Pendente":
                QMessageBox.warning(self, "Juiz obrigatório",
                                    "Registre a validação do juiz (Confirmado/Inválido) antes de salvar.")
                return
            if juiz_status == "Inválido" and not notas_juiz:
                QMessageBox.warning(self, "Notas obrigatórias",
                                    "Preencha as observações do juiz para tentativas inválidas.")
                return
            # Validação da avaliação automática
            if not self.last_eval_summary:
                QMessageBox.warning(self, "Avaliação obrigatória",
                                    "Execute a avaliação automática antes de salvar.")
                return
            last = (self.current_rep_data[-1] if self.current_rep_data
                    else {"valid": True if (self.auto_result == "Válido") else False})
            athlete = self.athlete_combo.currentText() or "Atleta"
            exercise = self.exercise_combo.currentText()
            attempt = str(self.attempt_spin.value())
            auto = "Válido" if last.get('valid') else "Inválido"
            juiz = self.last_judge_decision or "Pendente"
            hora = time.strftime("%d/%m/%Y %H:%M")

            # Garante diretório
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            storage = os.path.join(base, 'storage')
            os.makedirs(storage, exist_ok=True)
            path = os.path.join(storage, 'historico.csv')

            # Escreve linha
            header_needed = not os.path.exists(path)
            with open(path, 'a', encoding='utf-8') as f:
                if header_needed:
                    f.write('Atleta,Exercício,Tentativa,Auto,Juiz,Hora\n')
                f.write(f'{athlete},{exercise},{attempt},{auto},{juiz},{hora}\n')

            # Persistência em banco de dados (SQLite)
            try:
                db_saved_id = None
                record = {
                    'created_at': time.strftime("%Y-%m-%d %H:%M:%S"),
                    'athlete': athlete,
                    'exercise': exercise,
                    'attempt': int(self.attempt_spin.value()),
                    'auto_valid': bool(last.get('valid')),
                    'auto_summary': self.last_eval_summary.copy() if self.last_eval_summary else {},
                    'judge_valid': True if (self.last_judge_decision == 'Confirmado') else False,
                    'judge_notes': notas_juiz,
                    'angles': self.last_angles.copy() if self.last_angles else {},
                }
                save_attempt(record)
                try:
                    from db.analysis_repository import AnalysisRepository
                    repo = AnalysisRepository()
                    try:
                        repo.create_schema()
                    except Exception:
                        pass
                    data = {
                        'ATLETA': athlete,
                        'EXERCICIO': exercise,
                        'TENTATIVA': int(self.attempt_spin.value()),
                        'AUTO_VALIDO': 1 if bool(last.get('valid')) else 0,
                        'AUTO_RESUMO_JSON': json.dumps(self.last_eval_summary or {}),
                        'ANGULOS_JSON': json.dumps(self.last_angles or {}),
                        'STATUS': 'Confirmado' if (self.last_judge_decision == 'Confirmado') else 'Inválido',
                        'OBSERVACAO_JUIZ': notas_juiz,
                        'JUIZ': '',
                    }
                    try:
                        _new_id = repo.create(data)
                        db_saved_id = _new_id
                        try:
                            if hasattr(self, 'status_label') and self.status_label:
                                self.status_label.setText(f"Salvo no banco (ID={_new_id})")
                        except Exception:
                            pass
                    except Exception as _e:
                        try:
                            log_warning(f"Falha ao salvar no banco: {_e}")
                        except Exception:
                            pass
                        # Fallback para conector simples
                        try:
                            from db.db_connection import DatabaseConnection
                            _dbc = DatabaseConnection()
                            _id2 = _dbc.save_analysis(data)
                            if _id2 is not None:
                                db_saved_id = _id2
                                try:
                                    if hasattr(self, 'status_label') and self.status_label:
                                        self.status_label.setText(f"Salvo no banco (ID={_id2})")
                                except Exception:
                                    pass
                        except Exception as _e2:
                            try:
                                log_warning(f"Fallback MSSQL falhou: {_e2}")
                            except Exception:
                                pass
                        try:
                            if hasattr(self, 'status_label') and self.status_label:
                                self.status_label.setText("Falha ao salvar no banco (offline)")
                        except Exception:
                            pass
                except Exception:
                    pass
            except Exception as e:
                try:
                    log_warning(f"Falha ao salvar no banco: {e}")
                except Exception:
                    pass
                try:
                    if hasattr(self, 'status_label') and self.status_label:
                        self.status_label.setText("Falha ao salvar no banco (offline)")
                except Exception:
                    pass

            try:
                self._refresh_history_from_db()
            except Exception:
                pass

            try:
                msg = f"Registro salvo em:\n{path}"
                try:
                    if db_saved_id is not None:
                        msg += f"\nBanco: ID={db_saved_id}"
                    else:
                        msg += "\nBanco: offline"
                except Exception:
                    pass
                QMessageBox.information(self, "Salvo", msg)
            except Exception:
                pass
        except Exception as e:
            QMessageBox.warning(
                self, "Erro", f"Falha ao salvar tentativa:\n{e}")

    # ====== Gestão de atletas ======
    def _storage_path(self):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        storage = os.path.join(root, 'storage')
        return storage


    def _load_athlete_list(self):
        path = self._athletes_json_path()
        try:
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                if isinstance(data, list):
                    # sanitiza e remove duplicatas preservando ordem
                    seen = set()
                    result = []
                    for name in data:
                        if not isinstance(name, str):
                            continue
                        n = name.strip()
                        if n and n not in seen:
                            seen.add(n)
                            result.append(n)
                    return result
        except Exception:
            pass
        return ["Atleta 1", "Atleta 2", "Atleta 3"]

    def _export_history_to_pdf(self):
        """Exporta histórico em PDF simples (texto) se reportlab não estiver disponível."""
        try:
            # Tenta usar reportlab
            from reportlab.lib.pagesizes import A4
            from reportlab.pdfgen import canvas
            path, _ = QFileDialog.getSaveFileName(
                self, "Exportar histórico", "historico.pdf", "PDF (*.pdf)")
            if not path:
                return
            c = canvas.Canvas(path, pagesize=A4)
            width, height = A4
            y = height - 50
            c.setFont("Helvetica", 12)
            c.drawString(50, y, "Histórico de Tentativas")
            y -= 30
            for i in range(self.history_tree.topLevelItemCount()):
                item = self.history_tree.topLevelItem(i)
                row = [item.text(col) for col in range(6)]
                c.drawString(50, y, ", ".join(row))
                y -= 20
                if y < 50:
                    c.showPage()
                    y = height - 50
            c.save()
            QMessageBox.information(
                self, "Exportado", f"PDF salvo em:\n{path}")
        except Exception:
            # Fallback para TXT
            path, _ = QFileDialog.getSaveFileName(
                self, "Exportar histórico", "historico.txt", "Text (*.txt)")
            if not path:
                return
            with open(path, 'w', encoding='utf-8') as f:
                f.write("Histórico de Tentativas\n")
                for i in range(self.history_tree.topLevelItemCount()):
                    item = self.history_tree.topLevelItem(i)
                    row = [item.text(col) for col in range(6)]
                    f.write(", ".join(row) + "\n")
            QMessageBox.information(
                self, "Exportado", f"TXT salvo em:\n{path}")

    def _clear_history(self):
        self.history_tree.clear()

    def _show_ipf_rules(self):
        exercise = self.exercise_combo.currentText()
        exercise_map = {"Agachamento": "squat",
                        "Levantamento Terra": "deadlift"}
        exercise_key = exercise_map.get(exercise, "squat")

        rules = self._get_ipf_rules_explanation(exercise_key)

        msg = QMessageBox(self)
        msg.setWindowTitle(f"Regras IPF - {exercise}")
        msg.setText(rules)
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {ui_style.BG_COLOR};
                color: {ui_style.TEXT_COLOR};
            }}
            QMessageBox QLabel {{
                color: {ui_style.TEXT_COLOR};
            }}
            QPushButton {{
                background-color: {ui_style.PRIMARY_COLOR};
                color: white;
                padding: 8px 15px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {ui_style.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: #1F84AD;
            }}
        """)
        msg.exec_()

    # ===== CONTROLES DE VÍDEO E SELEÇÃO =====
    def _on_video_click(self, event):
        x = event.pos().x()
        y = event.pos().y()

        click_x = x / (self.video_display.width() if hasattr(self, 'video_display') else self.video_label.width())
        click_y = y / (self.video_display.height() if hasattr(self, 'video_display') else self.video_label.height())

        print(f"Clique detectado em: ({click_x:.3f}, {click_y:.3f})")

        # Fluxo de anotação: quando armado, captura posição e pergunta comentário
        if getattr(self, 'annotation_arm', False):
            self.annotation_arm = False
            comment, ok = QInputDialog.getText(
                self, "Anotação", "Comentário para o frame atual:")
            if ok and comment:
                idx = getattr(self, 'current_frame_index', 0)
                entry = {'pos': (float(click_x), float(click_y)), 'text': str(comment)}
                self.annotations.setdefault(idx, []).append(entry)
                # Re-renderiza o frame atual com o marcador
                self._seek_to_frame(idx)
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Anotação adicionada no frame atual")
            return

        self.last_click_pos = (click_x, click_y)

    def _reset_selection(self):
        self.selected_person_id = None
        self.selection_label.setText("Nenhuma pessoa selecionada")
        self.status_label.setText(
            "Aguardando análise...\nClique em uma pessoa para analisar")
        self.status_label.setStyleSheet(f"""
            color: {COLOR_NEUTRAL}; 
            font-size: 12px; 
            padding: 10px; 
            background-color: {ui_style.SURFACE_COLOR};
            border-radius: 6px;
            border-left: 4px solid {ui_style.PRIMARY_COLOR};
            min-height: 80px;
        """)
        print("Seleção resetada")

    def _find_person_at_click(self, pose_landmarks, click_pos):
        if pose_landmarks is None:
            return None

        landmarks = pose_landmarks.landmark
        visible_landmarks = [lm for lm in landmarks if lm.visibility > 0.3]

        if not visible_landmarks:
            return None

        min_x = min(lm.x for lm in visible_landmarks)
        max_x = max(lm.x for lm in visible_landmarks)
        min_y = min(lm.y for lm in visible_landmarks)
        max_y = max(lm.y for lm in visible_landmarks)

        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2

        click_x, click_y = click_pos
        if (min_x <= click_x <= max_x and min_y <= click_y <= max_y):
            return {
                'center': (center_x, center_y),
                'bbox': (min_x, min_y, max_x, max_y)
            }

        return None

    def _load_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Abrir vídeo", "", "Vídeos (*.mp4 *.avi *.mov)")
        if path:
            self.cap = cv2.VideoCapture(path)
            # Informações do vídeo
            try:
                self.total_frames = int(self.cap.get(
                    cv2.CAP_PROP_FRAME_COUNT) or 0)
                self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 30.0)
                if not self.fps or self.fps <= 1:
                    self.fps = 30.0
                self.base_interval_ms = int(1000.0 / self.fps)
                self.current_frame_index = int(
                    self.cap.get(cv2.CAP_PROP_POS_FRAMES) or 0)
            except Exception:
                self.total_frames = 0
                self.fps = 30.0
                self.base_interval_ms = 33
                self.current_frame_index = 0
            # Atualiza barra de progresso e rótulo de tempo
            try:
                if hasattr(self, 'yt_bar'):
                    self.yt_bar.setTotal(self.total_frames)
                    self.yt_bar.setFps(self.fps)
                    self.yt_bar.setValue(self.current_frame_index)
                if hasattr(self, 'yt_time_label'):
                    self._update_time_label()
            except Exception:
                pass
            # Ajusta a razão de aspecto com base no vídeo carregado
            try:
                w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                if w > 0 and h > 0:
                    self.responsive_ratio = w / h
                else:
                    ok, fr = self.cap.read()
                    if ok:
                        fh, fw = fr.shape[:2]
                        if fw > 0 and fh > 0:
                            self.responsive_ratio = fw / fh
                    # Volta para o primeiro frame
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.current_frame_index = 0
            except Exception:
                pass
            self._resize_video_area()
            self._start_analysis()
            self._reset_counters()
            if hasattr(self, 'video_display'):
                self.video_display.setText("")
                self.video_display.setStyleSheet(
                    f"background-color: #000000; border: 2px solid {ui_style.BORDER_COLOR}; border-radius: 6px;")
            self._reset_selection()
            # Zera trajetória da barra
            self.bar_path_points = []
            # Desabilita controles de navegação para fluxo ao vivo
            if hasattr(self, 'frame_slider'):
                self.frame_slider.setEnabled(False)
                self.frame_slider.setRange(0, 0)
                self.frame_slider.setValue(0)
            if hasattr(self, 'prev_frame_btn'):
                self.prev_frame_btn.setEnabled(False)
            if hasattr(self, 'next_frame_btn'):
                self.next_frame_btn.setEnabled(False)
            if hasattr(self, 'annotate_btn'):
                self.annotate_btn.setEnabled(False)
            if hasattr(self, 'frame_info_label'):
                self.frame_info_label.setText("Frame: 0/0")
            # Configura barra do player (respeita travamento)
            if not getattr(self, '_player_controls_locked', False):
                if hasattr(self, 'frame_slider'):
                    self.frame_slider.setEnabled(self.total_frames > 0)
                    self.frame_slider.setRange(0, max(0, self.total_frames - 1))
                    self.frame_slider.setValue(self.current_frame_index)
                if hasattr(self, 'prev_frame_btn'):
                    self.prev_frame_btn.setEnabled(self.total_frames > 0)
                if hasattr(self, 'next_frame_btn'):
                    self.next_frame_btn.setEnabled(self.total_frames > 0)
                if hasattr(self, 'annotate_btn'):
                    self.annotate_btn.setEnabled(self.total_frames > 0)
            if hasattr(self, 'frame_info_label'):
                self.frame_info_label.setText(
                    f"Frame: {self.current_frame_index}/{max(0, self.total_frames - 1)}")
            if hasattr(self, 'yt_time_label'):
                self._update_time_label()

    def _start_camera(self):
        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            QMessageBox.critical(
                self, "Erro", "Não foi possível acessar a câmera!")
        else:
           
            self._freeze_controls_layout = True
            # Ajustes de player para câmera
            self.total_frames = 0
            self.current_frame_index = 0
            try:
                self.fps = float(self.cap.get(cv2.CAP_PROP_FPS) or 30.0)
                if not self.fps or self.fps <= 1:
                    self.fps = 30.0
                self.base_interval_ms = int(1000.0 / self.fps)
            except Exception:
                self.fps = 30.0
                self.base_interval_ms = 33
            # Atualiza barra e tempo para modo câmera
            try:
                if hasattr(self, 'yt_bar'):
                    self.yt_bar.setTotal(0)
                    self.yt_bar.setFps(self.fps)
                    self.yt_bar.setValue(0)
                if hasattr(self, 'yt_time_label'):
                    self._update_time_label()
            except Exception:
                pass
            # Ajusta a razão de aspecto com base na câmera
            try:
                w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
                h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
                if w > 0 and h > 0:
                    self.responsive_ratio = w / h
            except Exception:
                pass
            self._resize_video_area()
            self._start_analysis()
            self._reset_counters()
            # Limpa texto/estilo na nova label independente
            if hasattr(self, 'video_display'):
                self.video_display.setText("")
                self.video_display.setStyleSheet(
                    f"background-color: #000000; border: 2px solid {ui_style.BORDER_COLOR}; border-radius: 6px;")
            self._reset_selection()
            # Zera trajetória da barra
            self.bar_path_points = []
   

    def change_theme(self, theme_name: str):
        try:
            apply_theme(theme_name)
            os.environ['POWERLIFT_THEME'] = theme_name
            app = QApplication.instance()
            if app:
                app.setStyleSheet(get_global_styles())
            self.setStyleSheet(get_global_styles() + self._get_stylesheet())
            if hasattr(self, 'act_theme_light'):
                self.act_theme_light.setChecked(theme_name == 'LightDefault')
            if hasattr(self, 'act_theme_dark'):
                self.act_theme_dark.setChecked(theme_name == 'AuroraDark')
        except Exception:
            pass

    def open_settings_dialog(self):
        # Diálogo de configurações removido (tema fixo)
        return

    def _analyze_frame(self, frame):
        # Detecta interrupção de câmera por congelamento de frames
        try:
            cur_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self._prev_frame_gray is not None and self.timer.isActive():
                diff = cv2.absdiff(cur_gray, self._prev_frame_gray)
                mean_diff = float(np.mean(diff)) / 255.0
                if mean_diff <= self._freeze_diff_threshold:
                    self._interruption_counter += 1
                else:
                    self._interruption_counter = 0
                self.camera_interrupted = bool(self._interruption_counter >= self._freeze_min_frames)
            self._prev_frame_gray = cur_gray
        except Exception:
            pass

        img_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.holistic.process(img_rgb)

        if self.last_click_pos and results.pose_landmarks:
            person_info = self._find_person_at_click(
                results.pose_landmarks, self.last_click_pos)
            if person_info:
                self.selected_person_id = 1
                self.selection_label.setText(
                    f"Pessoa {self.selected_person_id} selecionada")
                print(f"Pessoa {self.selected_person_id} selecionada!")
            else:
                print("Nenhuma pessoa encontrada na posição clicada")

            self.last_click_pos = None

        if results.pose_landmarks:
            # Seleção automática: se houver landmarks e nenhuma pessoa estiver selecionada
            if self.selected_person_id is None:
                self.selected_person_id = 1
                try:
                    self.selection_label.setText("Pessoa 1 selecionada (auto)")
                    if hasattr(self, 'status_label'):
                        self.status_label.setText("Análise ativa")
                except Exception:
                    pass

            if self.selected_person_id == 1:
                hex_color = ui_style.PRIMARY_COLOR.lstrip('#')
                r = int(hex_color[0:2], 16)
                g = int(hex_color[2:4], 16)
                b = int(hex_color[4:6], 16)
                color = (b, g, r)
                line_color = (255, 255, 255)
                if self.show_landmarks:
                    self._draw_landmarks_with_analysis(
                        frame, results, color, line_color)
            else:
                color = (128, 128, 128)
                line_color = (128, 128, 128)
                if self.show_landmarks:
                    self._draw_landmarks_simple(
                        frame, results, color, line_color)

                cv2.putText(frame, "CLIQUE EM UM ATLETA PARA ANALISAR",
                            (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        # Trajetória da barra
        try:
            if self.show_bar_path and results.pose_landmarks:
                h, w = frame.shape[:2]
                lms = results.pose_landmarks.landmark
                # Seleciona pontos conforme exercício
                ex = self.exercise_combo.currentText().lower(
                ) if hasattr(self, 'exercise_combo') else ''
                if 'agachamento' in ex:
                    ls = mp.solutions.pose.PoseLandmark.LEFT_SHOULDER.value
                    rs = mp.solutions.pose.PoseLandmark.RIGHT_SHOULDER.value
                    x1, y1 = int(lms[ls].x * w), int(lms[ls].y * h)
                    x2, y2 = int(lms[rs].x * w), int(lms[rs].y * h)
                else:
                    lw = mp.solutions.pose.PoseLandmark.LEFT_WRIST.value
                    rw = mp.solutions.pose.PoseLandmark.RIGHT_WRIST.value
                    x1, y1 = int(lms[lw].x * w), int(lms[lw].y * h)
                    x2, y2 = int(lms[rw].x * w), int(lms[rw].y * h)
                bx, by = (x1 + x2) // 2, (y1 + y2) // 2
                # Acumula pontos e limita comprimento
                self.bar_path_points.append((bx, by))
                if len(self.bar_path_points) > self.bar_path_max_points:
                    self.bar_path_points = self.bar_path_points[-self.bar_path_max_points:]
                # Desenha caminho
                self._draw_bar_path(frame)
        except Exception:
            pass

        # Desenha grade se habilitada
        if getattr(self, 'show_grid', False):
            self._draw_grid(frame)

        # Marcadores de anotações sobrepostos no frame atual
        try:
            self._draw_annotations(frame)
        except Exception:
            pass

        # Overlay de luzes IPF sobre o vídeo
        try:
            self._draw_ipf_lights_overlay(frame)
        except Exception:
            pass

        return frame

    def _toggle_grid(self, checked):
        self.show_grid = checked
        # Sincroniza checkbox e ação sem recursão
        if hasattr(self, 'grid_check'):
            bs = self.grid_check.blockSignals(True)
            self.grid_check.setChecked(checked)
            self.grid_check.blockSignals(bs)
        if hasattr(self, 'toggleGridAction'):
            bs2 = self.toggleGridAction.blockSignals(True)
            self.toggleGridAction.setChecked(checked)
            self.toggleGridAction.blockSignals(bs2)

    def _toggle_bar_path(self, checked):
        self.show_bar_path = checked
        # Sincroniza checkbox e ação sem recursão
        if hasattr(self, 'bar_path_check'):
            bs = self.bar_path_check.blockSignals(True)
            self.bar_path_check.setChecked(checked)
            self.bar_path_check.blockSignals(bs)
        if hasattr(self, 'toggleBarPathAction'):
            bs2 = self.toggleBarPathAction.blockSignals(True)
            self.toggleBarPathAction.setChecked(checked)
            self.toggleBarPathAction.blockSignals(bs2)

    def _draw_grid(self, frame, rows=None, cols=None, alpha=None, thickness=None):
        h, w = frame.shape[:2]
        overlay = frame.copy()

        def hex_to_bgr(hex_color):
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (b, g, r)
        line_color = hex_to_bgr(ui_style.BORDER_COLOR)
        rows = self.grid_rows if rows is None else rows
        cols = self.grid_cols if cols is None else cols
        alpha = self.grid_alpha if alpha is None else alpha
        thickness = self.grid_thickness if thickness is None else thickness
        for i in range(1, rows):
            y = int(i * h / rows)
            cv2.line(overlay, (0, y), (w, y),
                     line_color, thickness, cv2.LINE_AA)
        for j in range(1, cols):
            x = int(j * w / cols)
            cv2.line(overlay, (x, 0), (x, h),
                     line_color, thickness, cv2.LINE_AA)
        cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)

    def _draw_bar_path(self, frame):
        if len(self.bar_path_points) < 2:
            return

        def hex_to_bgr(hex_color):
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (b, g, r)
        color = hex_to_bgr(ui_style.PRIMARY_COLOR)
        for i in range(1, len(self.bar_path_points)):
            cv2.line(frame, self.bar_path_points[i-1], self.bar_path_points[i],
                     color, self.bar_path_thickness, cv2.LINE_AA)

    def _draw_annotations(self, frame):
        idx = getattr(self, 'current_frame_index', 0)
        entries = self.annotations.get(idx, [])
        if not entries:
            return
        h, w = frame.shape[:2]
        def hex_to_bgr(hex_color):
            hex_color = hex_color.lstrip('#')
            r = int(hex_color[0:2], 16)
            g = int(hex_color[2:4], 16)
            b = int(hex_color[4:6], 16)
            return (b, g, r)
        color = hex_to_bgr(ui_style.PRIMARY_COLOR)
        for entry in entries:
            cx = int(max(0.0, min(1.0, entry.get('pos', (0.05, 0.05))[0])) * w)
            cy = int(max(0.0, min(1.0, entry.get('pos', (0.05, 0.05))[1])) * h)
            cv2.circle(frame, (cx, cy), 8, color, -1, lineType=cv2.LINE_AA)
            txt = str(entry.get('text', '')).strip()
            if txt:
                cv2.putText(frame, txt, (cx + 10, cy - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

    def _activate_ipf_overlay(self, lights: list):
        """Ativa overlay temporário das luzes IPF sobre o vídeo."""
        try:
            self._ipf_lights_current = list(lights or [])
            now_ms = int(time.time() * 1000)
            self._ipf_overlay_start_ms = now_ms
            self._ipf_overlay_until_ms = now_ms + int(self.ipf_overlay_duration_sec * 1000)
        except Exception:
            pass

    def _draw_ipf_lights_overlay(self, frame):
        """Desenha três círculos (brancas/vermelhas) com fade in/out no topo."""
        try:
            if not getattr(self, 'show_ipf_lights_overlay', False):
                return
            if not getattr(self, '_ipf_lights_current', None):
                return
            now_ms = int(time.time() * 1000)
            if now_ms > getattr(self, '_ipf_overlay_until_ms', 0):
                self._ipf_lights_current = []
                return

            start = getattr(self, '_ipf_overlay_start_ms', now_ms)
            end = getattr(self, '_ipf_overlay_until_ms', now_ms)
            fade = int(getattr(self, 'ipf_overlay_fade_ms', 250))
            if now_ms - start < fade:
                alpha = (now_ms - start) / max(fade, 1)
            elif end - now_ms < fade:
                alpha = (end - now_ms) / max(fade, 1)
            else:
                alpha = 1.0
            alpha = max(0.0, min(1.0, alpha))

            overlay = frame.copy()
            h, w = frame.shape[:2]
            radius = max(14, int(min(w, h) * 0.02))
            spacing = radius * 3
            cx = w // 2
            cy = int(h * 0.15)
            centers = [
                (cx - spacing, cy),
                (cx, cy),
                (cx + spacing, cy)
            ]
            for idx, c in enumerate(centers):
                color = (255, 255, 255) if (idx < len(self._ipf_lights_current) and self._ipf_lights_current[idx] == 'white') else (0, 0, 255)
                cv2.circle(overlay, c, radius, color, -1)
                cv2.circle(overlay, c, radius, (30, 30, 30), 2)
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
        except Exception:
            pass

    def _draw_landmarks_simple(self, frame, results, color, line_color):
        self.mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks,
            self.mp_holistic.POSE_CONNECTIONS,
            self.mp_drawing.DrawingSpec(
                color=color, thickness=2, circle_radius=2),
            self.mp_drawing.DrawingSpec(color=line_color, thickness=2)
        )

    def _draw_landmarks_with_analysis(self, frame, results, color, line_color):
        self.mp_drawing.draw_landmarks(
            frame,
            results.pose_landmarks,
            self.mp_holistic.POSE_CONNECTIONS,
            self.mp_drawing.DrawingSpec(
                color=color, thickness=3, circle_radius=3),
            self.mp_drawing.DrawingSpec(color=line_color, thickness=2)
        )

        landmarks = results.pose_landmarks.landmark
        visible_landmarks = [lm for lm in landmarks if lm.visibility > 0.3]

        if visible_landmarks:
            min_x = min(lm.x for lm in visible_landmarks)
            max_x = max(lm.x for lm in visible_landmarks)
            min_y = min(lm.y for lm in visible_landmarks)
            max_y = max(lm.y for lm in visible_landmarks)

            h, w = frame.shape[:2]
            bbox = (
                int(min_x * w), int(min_y * h),
                int(max_x * w), int(max_y * h)
            )

            cv2.rectangle(frame, (bbox[0], bbox[1]),
                          (bbox[2], bbox[3]), color, 2)
            cv2.putText(frame, f"Pessoa {self.selected_person_id}",
                        (bbox[0], bbox[1] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        if self.selected_person_id is not None:
            landmarks_dict = {}
            # Captura landmarks atuais e visibilidade
            current_lm = {}
            current_vis = {}
            for i, lm in enumerate(results.pose_landmarks.landmark):
                landmark_name = self._get_landmark_name(i)
                landmarks_dict[landmark_name] = (lm.x, lm.y, lm.z)
                current_lm[landmark_name] = {
                    'x': float(lm.x), 'y': float(lm.y), 'z': float(lm.z)
                }
                current_vis[landmark_name] = float(getattr(lm, 'visibility', 1.0))

            # Atualiza velocidades/acelerações para pontos usados no treino
            try:
                points = ['LEFT_HIP', 'RIGHT_HIP', 'LEFT_SHOULDER']
                coords = ['x', 'y']
                for pt in points:
                    for cd in coords:
                        prev_val = (self.prev_lm.get(pt, {}) or {}).get(cd)
                        cur_val = current_lm.get(pt, {}).get(cd)
                        if prev_val is not None and cur_val is not None:
                            vel = cur_val - prev_val
                            prev_vel = self.last_vel.get((pt, cd))
                            acc = (vel - prev_vel) if prev_vel is not None else 0.0
                            self.last_vel[(pt, cd)] = vel
                            self.last_acc[(pt, cd)] = acc
                        else:
                            # Inicializa com zero para primeira amostra
                            self.last_vel[(pt, cd)] = self.last_vel.get((pt, cd), 0.0)
                            self.last_acc[(pt, cd)] = self.last_acc.get((pt, cd), 0.0)
                # Atualiza estados anteriores e atuais
                self.prev_lm = self.last_lm.copy()
                # Persiste visibilidade junto
                self.last_lm = {k: {**v, 'visibility': current_vis.get(k, 1.0)} for k, v in current_lm.items()}
            except Exception:
                # Se algo falhar, garante pelo menos atualização dos atuais
                self.prev_lm = getattr(self, 'last_lm', {})
                self.last_lm = {k: {**v, 'visibility': current_vis.get(k, 1.0)} for k, v in current_lm.items()}

            exercise = self.exercise_combo.currentText()
            exercise_map = {"Agachamento": "squat",
                            "Levantamento Terra": "deadlift"}
            exercise_key = exercise_map.get(exercise, "squat")

            angles = self.angle_calculator.calculate_joint_angles_advanced(
                landmarks_dict, exercise_key)
            # Suaviza ângulos antes de calcular estabilidade e avaliações
            angles_sm = self._apply_smoothing(angles)
            stability = self._calculate_stability(angles_sm)

            # Se houver modelo treinado e a opção estiver ativa, usa avaliação por modelo
            model_eval = None
            if getattr(self, 'use_model_inference', False) and self.model and self.feature_names:
                model_eval = self._evaluate_with_model(
                    angles_sm, stability, exercise)

            if model_eval:
                if self._should_display_evaluation():
                    self._display_ipf_feedback(model_eval, angles_sm, exercise)
                else:
                    self._hide_evaluation_status()
                evaluation = model_eval
            else:
                # Avaliação aprimorada baseada em regras (fallback padrão)
                try:
                    enhanced_evaluation = (
                        self.enhanced_scoring.evaluate_squat(
                            angles_sm, stability)
                        if exercise_key == "squat"
                        else self.enhanced_scoring.evaluate_deadlift(angles_sm, stability)
                    )
                    if self._should_display_evaluation():
                        self._display_enhanced_feedback(enhanced_evaluation)
                    else:
                        self._hide_evaluation_status()
                    evaluation = enhanced_evaluation
                except Exception as e:
                    print(f"Erro na avaliação aprimorada: {e}")
                    detailed = (
                        self.enhanced_scoring.evaluate_squat(
                            angles_sm, stability)
                        if exercise_key == "squat"
                        else self.enhanced_scoring.evaluate_deadlift(angles_sm, stability)
                    )
                    evaluation = detailed
                    # Converte para formato básico para o painel IPF
                    basic_eval = self._convert_detailed_to_basic(evaluation)
                    if self._should_display_evaluation():
                        self._display_ipf_feedback(basic_eval, angles_sm, exercise)
                    else:
                        self._hide_evaluation_status()
            # Registrar amostra para aprendizado contínuo
            try:
                self._record_runtime_sample(angles_sm, stability, evaluation, exercise)
            except Exception:
                pass
            self._detect_rep_cycle(angles_sm, evaluation, exercise)

            for key, label in self.angle_labels.items():
                if key in angles_sm:
                    label.setText(
                        f"{label.text().split(':')[0]}: {angles_sm[key]:.1f}°")

            payload = {
                'angles': angles_sm,
                'evaluation': evaluation,
                'rep_count': self.rep_count,
                'last_rep_metrics': (self.current_rep_data[-1]['metrics'] if getattr(self, 'current_rep_data', None) and len(self.current_rep_data) > 0 else None),
                'exercise': exercise,
                'timestamp': time.time()
            }
            self.last_analysis = payload
            self.analysisUpdated.emit(payload)

        return frame

    def _should_display_evaluation(self) -> bool:
        try:
            if getattr(self, 'always_show_evaluation', True):
                return True
            if not self.timer.isActive():
                return True
            return bool(self.camera_interrupted)
        except Exception:
            return True

    def _hide_evaluation_status(self):
        """Oculta avaliação durante reprodução contínua, mantendo feedback neutro."""
        try:
            if hasattr(self, 'status_label'):
                self.status_label.setText("Processando…")
                self.status_label.setStyleSheet(f"""
                    color: {COLOR_NEUTRAL};
                    font-weight: normal;
                    background-color: rgba(125, 125, 125, 0.06);
                    padding: 10px;
                    border-radius: 6px;
                    border-left: 4px solid {COLOR_NEUTRAL};
                    min-height: 60px;
                """)
        except Exception:
            pass

    def _record_runtime_sample(self, angles: dict, stability: float, evaluation: object, exercise: str):
        """Registra amostras em buffer para aprendizado contínuo (rótulo 1=normal, 0=anomalia)."""
        try:
            valid = False
            if isinstance(evaluation, dict):
                valid = bool(evaluation.get('valid', False))
            else:
                # DetailedEvaluation: considera válido se percentage >= 60
                valid = bool(getattr(evaluation, 'percentage', 0.0) >= 60.0)
            sample = {
                'timestamp': float(time.time()),
                'exercise': str(exercise),
                'label': int(1 if valid else 0),
                'knee_angle': float(angles.get('knee_angle', np.nan)),
                'hip_angle': float(angles.get('hip_angle', np.nan)),
                'torso_angle': float(angles.get('torso_angle', np.nan)),
                'back_angle': float(angles.get('back_angle', np.nan)),
                'stability': float(stability),
            }
            self._runtime_samples.append(sample)
            if len(self._runtime_samples) >= self._runtime_buffer_limit or (not self.timer.isActive()):
                self._flush_runtime_buffer()
        except Exception:
            pass

    def _flush_runtime_buffer(self):
        """Salva o buffer de amostras em CSV incremental para consumo pelo pipeline de treino."""
        try:
            import pandas as pd
            base_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'dataset', 'runtime_buffer')
            os.makedirs(base_dir, exist_ok=True)
            out_path = os.path.join(base_dir, f"runtime_session_{self._runtime_session_id}.csv")
            df = pd.DataFrame(self._runtime_samples)
            if os.path.exists(out_path):
                df.to_csv(out_path, mode='a', header=False, index=False)
            else:
                df.to_csv(out_path, index=False)
            self._runtime_samples.clear()
        except Exception:
            # Silencioso: não bloquear fluxo em caso de erro de disco
            self._runtime_samples.clear()

    def _convert_detailed_to_basic(self, evaluation):
        """Converte DetailedEvaluation em dict básico usado no painel IPF."""
        try:
            lights = list(getattr(evaluation, 'ipf_lights', []) or [])
            valid = lights.count('white') >= 2
            return {
                'valid': valid,
                'score': float(getattr(evaluation, 'total_score', 0.0)),
                'max_score': float(getattr(evaluation, 'max_score', 0.0)),
                'lights': lights,
                'feedback': list(getattr(evaluation, 'overall_feedback', []) or []),
                'quality': float(getattr(evaluation, 'movement_quality_index', 0.0)),
            }
        except Exception:
            return {'valid': False, 'score': 0, 'max_score': 0, 'lights': ['red', 'red', 'red'], 'feedback': [], 'quality': 0.0}

    def _compute_rep_phases(self, stream):
        """Duração das fases excêntrica e concêntrica pela variação do ângulo do joelho."""
        try:
            if not stream or len(stream) < 2:
                return {'eccentric': 0.0, 'concentric': 0.0}
            ecc, con = 0.0, 0.0
            for i in range(1, len(stream)):
                dt = max(1e-3, stream[i]['t'] - stream[i-1]['t'])
                dk = (stream[i]['knee'] or 0) - (stream[i-1]['knee'] or 0)
                if dk < 0:
                    ecc += dt
                else:
                    con += dt
            return {'eccentric': round(ecc, 3), 'concentric': round(con, 3)}
        except Exception:
            return {'eccentric': 0.0, 'concentric': 0.0}

    def _compute_rep_velocity(self, stream):
        """Velocidade média baseada na variação do ângulo do joelho."""
        try:
            if not stream or len(stream) < 2:
                return 0.0
            total_time = max(1e-3, stream[-1]['t'] - stream[0]['t'])
            delta_angle = abs(
                (stream[-1]['knee'] or 0) - (stream[0]['knee'] or 0))
            return round(delta_angle / total_time, 3)
        except Exception:
            return 0.0

    def _bar_path_metrics_over_window(self, points):
        """Comprimento e retidão (0..1) da trajetória da barra no intervalo acumulado."""
        try:
            if not points or len(points) < 2:
                return {'length': 0.0, 'straightness': 1.0}
            length = 0.0
            for i in range(1, len(points)):
                x1, y1 = points[i-1]
                x2, y2 = points[i]
                length += math.hypot(x2 - x1, y2 - y1)
            x0, y0 = points[0]
            xN, yN = points[-1]
            direct = math.hypot(xN - x0, yN - y0)
            straightness = float(
                min(1.0, max(0.0, direct / max(1e-3, length))))
            return {'length': round(length, 2), 'straightness': round(straightness, 3)}
        except Exception:
            return {'length': 0.0, 'straightness': 1.0}

    # ===== Novas funções úteis =====
    def _export_history_to_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Exportar histórico", "historico.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            import csv
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["Atleta", "Exercício", "Tent.", "Auto", "Juiz", "Hora"])
                for i in range(self.history_tree.topLevelItemCount()):
                    item = self.history_tree.topLevelItem(i)
                    row = [item.text(c) for c in range(6)]
                    writer.writerow(row)
            QMessageBox.information(
                self, "Exportar CSV", "Histórico exportado com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao exportar CSV: {e}")

    def _capture_frame(self):
        target_label = self.video_display if hasattr(self, 'video_display') else self.video_label
        if target_label.pixmap() is None:
            QMessageBox.warning(
                self, "Aviso", "Nenhum frame disponível para salvar.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar frame", "frame.png", "PNG (*.png)")
        if not path:
            return
        try:
            target_label.pixmap().save(path, "PNG")
            QMessageBox.information(
                self, "Salvar Frame", "Imagem salva com sucesso!")
        except Exception as e:
            QMessageBox.critical(self, "Erro", f"Falha ao salvar imagem: {e}")

    def _save_analysis_snapshot(self):
        if not self.last_analysis:
            QMessageBox.warning(
                self, "Aviso", "Nenhum dado de análise disponível.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Salvar snapshot", "snapshot.json", "JSON (*.json)")
        if not path:
            return
        try:
            import json
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.last_analysis, f, ensure_ascii=False, indent=2)
            QMessageBox.information(
                self, "Snapshot", "Snapshot de análise salvo com sucesso!")
        except Exception as e:
            QMessageBox.critical(
                self, "Erro", f"Falha ao salvar snapshot: {e}")

    def _toggle_landmarks(self):
        self.show_landmarks = not self.show_landmarks
        state = "Ligados" if self.show_landmarks else "Desligados"
        self.status_label.setText(
            f"Landmarks {state}. {('Processando...' if self.timer.isActive() else 'Aguardando análise...')}")

    def showEvent(self, event):
        super().showEvent(event)
        if not self.isMaximized():
            self.showMaximized()
        self.windowStateVerified.emit(self.isMaximized())
        try:
            self._update_right_panel_width()
        except Exception:
            pass
        self._resize_video_area()
        try:
            self._update_bottom_controls_layout()
        except Exception:
            pass

    def _update_right_panel_width(self):
        """Define largura responsiva para o painel direito ocupando mais espaço sem rolagem."""
        if not hasattr(self, 'right_scroll') or self.right_scroll is None:
            return
        vw = max(1, self.width())
        try:
            target, _min_w, _max_w = compute_right_panel_width(vw)
        except Exception:
            # Fallback: 38% com limites mais altos
            target = int(max(480, min(740, vw * 0.38)))
        current = self.right_scroll.width()
        if abs(target - current) > 4:
            self.right_scroll.setFixedWidth(target)

    def _resize_video_area(self):
        if not hasattr(self, 'video_label'):
            return
        # Reserva a largura do painel direito de forma dinâmica + margem
        try:
            right_w = max(360, self.right_scroll.width()) if hasattr(
                self, 'right_scroll') and self.right_scroll else 500
        except Exception:
            right_w = 500
        available_w = self.width() - (right_w + 40)
        # Reserva adicional para a barra do player e os botões inferiores, usando alturas reais
        # Usa alturas fixas previamente calculadas para estabilidade
        try:
            controls_h = getattr(self, '_fixed_controls_height', 0)
        except Exception:
            controls_h = 0
        try:
            player_h = getattr(self, '_fixed_player_height', 0)
        except Exception:
            player_h = 0
        # Margem base menor + alturas reais (+folga)
        # Reduz a reserva para ampliar área de vídeo
        # Em modo retrato (w/h pequeno), liberar mais altura para evitar corte
        # Área fixa independente do vídeo: usa razão fixa quando lock_video_area estiver habilitado
        use_fixed = getattr(self, 'lock_video_area', False)
        aspect_ratio = (getattr(self, 'fixed_video_ratio', 16.0/9.0) if use_fixed else getattr(self, 'responsive_ratio', 1.0))
        is_portrait = True if aspect_ratio <= 0.75 else False
        base_reserved = (96) + max(0, player_h) + max(0, controls_h) + 20
        try:
            cap_h = int(self.height() * 0.56)
            if hasattr(self, 'video_frame') and self.video_frame:
                self.video_frame.setMaximumHeight(max(340, cap_h))
        except Exception:
            pass
        available_h = self.height() - base_reserved
        # Teto de altura do vídeo para manter layout consistente
        max_video_h_cap = int(self.height() * (0.80))
        available_h = min(available_h, max_video_h_cap)
        if available_w <= 0 or available_h <= 0:
            return
        target_w = int(min(available_w, available_h * aspect_ratio))
        target_h = int(target_w / aspect_ratio)
        # Aplica tamanho e estilo na nova label independente
        if hasattr(self, 'video_display'):
            self.video_display.setFixedSize(target_w, target_h)
            self.video_display.setStyleSheet(
                "background-color: #000000; border: 3px solid #3A3A4D; border-radius: 8px;")
        # Ajusta o frame externo para acompanhar a largura do vídeo (+margens)
        try:
            if hasattr(self, 'video_frame') and self.video_frame:
                # margem interna definida em 10 de cada lado
                self.video_frame.setFixedWidth(target_w + 20)
        except Exception:
            pass
      
        try:
            self._update_player_button_sizes()
        except Exception:
            pass
        try:
            self._update_player_min_height()
        except Exception:
            pass
        try:
            self._update_player_controls_width()
        except Exception:
            pass
        try:
            self._update_controls_container_width()
        except Exception:
            pass
        try:
            self._update_controls_min_height()
        except Exception:
            pass
        # Reavalia o modo do layout dos botões com a largura final do vídeo
        try:
            self._update_bottom_controls_layout()
        except Exception:
            pass

    # ===== Layout responsivo dos botões inferiores =====
    def _rebuild_controls_layout(self, mode: str):
        """Reconstrói o layout dos botões inferiores como 'horizontal' ou 'grid'.
        Evita recriação desnecessária se o modo atual for o mesmo.
        """
        if not hasattr(self, 'controls_widget') or self.controls_widget is None:
            return
        # Evita reconstrução redundante
        current_mode = getattr(self, '_controls_layout_mode', None)
        if current_mode == mode:
            return

        # Cria/recupera layout raiz do container
        root_layout = self.controls_widget.layout()
        if root_layout is None:
            root_layout = QVBoxLayout(self.controls_widget)
            root_layout.setContentsMargins(0, 0, 0, 0)
            root_layout.setSpacing(6)

        # Remove container anterior, se houver
        if hasattr(self, 'controls_container') and self.controls_container is not None:
            try:
                root_layout.removeWidget(self.controls_container)
                self.controls_container.deleteLater()
            except Exception:
                pass

        # Novo container interno
        self.controls_container = QWidget(self.controls_widget)
        self.controls_container.setObjectName('controlsContainer')

        if mode == 'horizontal':
            layout = QHBoxLayout(self.controls_container)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(12)
            layout.addWidget(self.btn_video)
            layout.addWidget(self.btn_camera)
            layout.addWidget(self.reset_btn)
            # Distribui igualmente a largura entre os botões
            layout.setStretch(0, 1)
            layout.setStretch(1, 1)
            layout.setStretch(2, 1)
        else:
            layout = QGridLayout(self.controls_container)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setHorizontalSpacing(12)
            layout.setVerticalSpacing(12)
            layout.addWidget(self.btn_video, 0, 0)
            layout.addWidget(self.btn_camera, 0, 1)
            layout.addWidget(self.reset_btn, 1, 0)
            layout.setColumnStretch(0, 1)
            layout.setColumnStretch(1, 1)
        # Centraliza o container interno
        root_layout.addWidget(self.controls_container, alignment=Qt.AlignHCenter)
        self._controls_layout_mode = mode

        # Ajusta largura do container para alinhar com a área do vídeo
        try:
            self._update_controls_container_width()
        except Exception:
            pass

    def _update_bottom_controls_layout(self):
        """Determina o modo do layout inferior com base na largura útil.
        Mantém sempre o modo horizontal para não mover posições.
        """
        try:
            # Se o layout estiver congelado, não recalcula
            if getattr(self, '_freeze_controls_layout', False):
                return
            # Sempre usa horizontal para manter posições estáveis
            target_mode = 'horizontal'
            self._rebuild_controls_layout(target_mode)
        except Exception:
            pass

    def _update_controls_container_width(self):
        """Define uma largura fixa para o container dos botões, independente do vídeo."""
        if not hasattr(self, 'controls_widget'):
            return
        try:
            # Se o layout estiver congelado, mantém a largura fixa atual
            if getattr(self, '_freeze_controls_layout', False):
                return
            # Calcula uma largura fixa baseada nos mínimos dos botões
            spacing = 12 * 2  # dois espaços entre três botões
            margins_lr = 24   # somatório das margens esquerda/direita
            required_w = (
                self.btn_video.minimumWidth() +
                self.btn_camera.minimumWidth() +
                self.reset_btn.minimumWidth() +
                spacing + margins_lr
            )
            # Define largura estável baseada no cálculo atual
            self._controls_fixed_width = required_w
            self.controls_widget.setFixedWidth(self._controls_fixed_width)
        except Exception:
            pass
    def _update_player_controls_width(self):
        """Define uma largura fixa para a barra do player, independente do vídeo."""
        if not hasattr(self, 'player_controls'):
            return
        try:
            # Se o layout estiver congelado, não altera a largura da barra
            if getattr(self, '_freeze_controls_layout', False):
                return
            if getattr(self, '_player_controls_locked', False):
                # Quando travado, não aplicar largura
                return
            # Estima largura necessária somando largura dos grupos e espaçamentos
            spacing_lr = 24  # margens esquerda/direita internas
            row_spacing = 8 * 4  # espaçamentos entre grupos

            def _hint_w(obj):
                return obj.sizeHint().width() if obj else 0

            nav_w = (
                _hint_w(getattr(self, 'prev_frame_btn', None)) +
                _hint_w(getattr(self, 'play_pause_btn', None)) +
                _hint_w(getattr(self, 'next_frame_btn', None)) +
                _hint_w(getattr(self, 'fullscreen_btn', None))
            )
            speed_label_w = QLabel("Velocidade:").sizeHint().width()
            speed_w = _hint_w(getattr(self, 'speed_combo', None)) + speed_label_w
            info_w = (
                _hint_w(getattr(self, 'frame_info_label', None)) +
                _hint_w(getattr(self, 'annotate_btn', None))
            )

            required_w = nav_w + speed_w + info_w + row_spacing + spacing_lr
            # Largura mínima confortável caso sizeHints retornem muito pequenos
            required_w = max(520, required_w)
            self._player_controls_fixed_width = required_w
            self.player_controls.setFixedWidth(required_w)
        except Exception:
            pass

    def _update_controls_min_height(self):
        """Define uma altura mínima para a área dos botões, evitando corte."""
        try:
            if getattr(self, '_freeze_controls_layout', False):
                return
            # Calcula altura necessária para horizontal e para grid, usa o maior
            btn_h = max(self.btn_video.sizeHint().height(), 40)
            margin_tb = 20  # soma das margens superior e inferior
            min_h_horizontal = 1 * btn_h + 0 + margin_tb
            min_h_grid = 2 * btn_h + 12 + margin_tb
            fixed_h = max(min_h_horizontal, min_h_grid)
            # Persiste altura fixa para estabilidade do layout
            self._fixed_controls_height = fixed_h
            if hasattr(self, 'controls_container') and self.controls_container:
                self.controls_container.setFixedHeight(fixed_h)
            if hasattr(self, 'controls_widget') and self.controls_widget:
                self.controls_widget.setFixedHeight(fixed_h)
        except Exception:
            pass

    def _update_player_min_height(self):
        """Define altura mínima dinâmica para a barra do player."""
        try:
            if getattr(self, '_player_controls_locked', False):
                # Quando travado, barra do player não ocupa espaço
                self._fixed_player_height = 0
                if hasattr(self, 'player_controls') and self.player_controls:
                    self.player_controls.setFixedHeight(0)
                return
            # Usa altura da barra customizada quando disponível; caso contrário, usa slider
            if hasattr(self, 'yt_bar') and self.yt_bar:
                slider_h = max(24, self.yt_bar.sizeHint().height())
            else:
                slider_h = self.frame_slider.sizeHint().height() if hasattr(self, 'frame_slider') and self.frame_slider else 24
            # Altura máxima entre botões e combo
            comp_h = [
                getattr(self, 'prev_frame_btn', None),
                getattr(self, 'play_pause_btn', None),
                getattr(self, 'next_frame_btn', None),
                getattr(self, 'annotate_btn', None)
            ]
            btn_h = max([w.sizeHint().height() for w in comp_h if w] + [36])
            combo_h = self.speed_combo.sizeHint().height() if hasattr(self, 'speed_combo') and self.speed_combo else 32
            row_h = max(btn_h, combo_h)
            spacing = 8
            margins_tb = 20  # 10 em cima e 10 embaixo
            min_h = slider_h + spacing + row_h + margins_tb
            # Persiste altura fixa para estabilidade do layout
            self._fixed_player_height = min_h
            if hasattr(self, 'player_controls') and self.player_controls:
                self.player_controls.setFixedHeight(min_h)
        except Exception:
            pass

    def _disable_player_controls_permanently(self):
        """Oculta, desativa e desconecta todos os controles do player de vídeo."""
        # Ocultar container
        if hasattr(self, 'player_controls') and self.player_controls:
            self.player_controls.setVisible(False)
            self.player_controls.setFixedHeight(0)
            self.player_controls.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            self.player_controls.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.player_controls.setFocusPolicy(Qt.NoFocus)
            self.player_controls.setContextMenuPolicy(Qt.NoContextMenu)
        # Slider
        if hasattr(self, 'frame_slider') and getattr(self, 'frame_slider', None):
            try:
                self.frame_slider.valueChanged.disconnect()
                self.frame_slider.sliderPressed.disconnect()
                self.frame_slider.sliderReleased.disconnect()
            except Exception:
                pass
            self.frame_slider.setEnabled(False)
            self.frame_slider.setVisible(False)
            self.frame_slider.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.frame_slider.setFocusPolicy(Qt.NoFocus)
        # Botões
        for name in ['prev_frame_btn', 'play_pause_btn', 'next_frame_btn', 'annotate_btn']:
            btn = getattr(self, name, None)
            if btn:
                try:
                    btn.clicked.disconnect()
                except Exception:
                    pass
                btn.setEnabled(False)
                btn.setVisible(False)
                btn.setAttribute(Qt.WA_TransparentForMouseEvents, True)
                btn.setFocusPolicy(Qt.NoFocus)
        # Combo de velocidade
        if hasattr(self, 'speed_combo') and getattr(self, 'speed_combo', None):
            try:
                self.speed_combo.currentTextChanged.disconnect()
            except Exception:
                pass
            self.speed_combo.setEnabled(False)
            self.speed_combo.setVisible(False)
            self.speed_combo.setAttribute(Qt.WA_TransparentForMouseEvents, True)
            self.speed_combo.setFocusPolicy(Qt.NoFocus)

    def _start_analysis(self):
        # Validação: exigir atleta e exercício antes de iniciar
        try:
            athlete_ok = bool((self.athlete_combo.currentText() or '').strip())
            exercise_ok = (self.exercise_combo.currentIndex() != 0)
            if not (athlete_ok and exercise_ok):
                try:
                    QMessageBox.information(self, "Campos obrigatórios",
                                            "Informe o nome do atleta e selecione o exercício para iniciar.")
                except Exception:
                    pass
                try:
                    if hasattr(self, 'status_label') and self.status_label:
                        self.status_label.setText("Preencha atleta e exercício para iniciar")
                except Exception:
                    pass
                if hasattr(self, 'play_pause_btn'):
                    self.play_pause_btn.setText("► Iniciar")
                return
        except Exception:
            pass
        if self.cap:
            interval_ms = compute_interval_ms(self.base_interval_ms, self.playback_speed)
            try:
                self.timer.start(interval_ms)
            except Exception:
                self.timer.start(30)
            if hasattr(self, 'play_pause_btn'):
                self.play_pause_btn.setText("⏸ Pausar")
            if hasattr(self, 'status_label'):
                self.status_label.setText("Processando...")
            # Antes de congelar, fixa dimensões para o estado atual
            try:
                self._update_controls_container_width()
                self._update_player_controls_width()
                self._update_controls_min_height()
                self._update_bottom_controls_layout()
            except Exception:
                pass
            # Congela o layout inferior enquanto o vídeo/câmera está em execução
            self._freeze_controls_layout = True
            
            if hasattr(self, 'analysisStateChanged'):
                try:
                    self.analysisStateChanged.emit(True)
                except Exception:
                    pass

    def _pause_analysis(self):
        self.timer.stop()
        if hasattr(self, 'play_pause_btn'):
            self.play_pause_btn.setText("► Iniciar")
        # Ao pausar, mantém a última análise exibida no painel
        try:
            last = getattr(self, 'last_analysis', None)
            ev = (last or {}).get('evaluation') if isinstance(last, dict) else None
            ang = (last or {}).get('angles', {}) if isinstance(last, dict) else {}
            ex = (last or {}).get('exercise') if isinstance(last, dict) else None
            if ev is not None:
                if isinstance(ev, dict):
                    # Avaliação básica IPF (dict)
                    self._display_ipf_feedback(ev, ang, ex or self._current_exercise_key())
                else:
                    # Avaliação detalhada (objeto)
                    self._display_enhanced_feedback(ev)
            else:
                if hasattr(self, 'status_label'):
                    self.status_label.setText("Vídeo pausado")
        except Exception:
            if hasattr(self, 'status_label'):
                self.status_label.setText("Vídeo pausado")
        # Descongela quando pausar
        self._freeze_controls_layout = False
        if hasattr(self, 'analysisStateChanged'):
            try:
                self.analysisStateChanged.emit(False)
            except Exception:
                pass
        if hasattr(self, 'yt_time_label'):
            self._update_time_label()

    def _update_time_label(self):
        """Atualiza o rótulo abaixo da barra com tempo atual/total em m:ss."""
        try:
            if not hasattr(self, 'yt_time_label'):
                return
            fps = float(getattr(self, 'fps', 30.0) or 30.0)
            if fps <= 1:
                fps = 30.0
            idx = int(getattr(self, 'current_frame_index', 0) or 0)
            tot = int(getattr(self, 'total_frames', 0) or 0)
            def fmt(sec: float) -> str:
                sec = max(0.0, float(sec or 0.0))
                m = int(sec // 60)
                s = int(sec % 60)
                return f"{m}:{s:02d}"
            cur = (idx / fps) if fps > 0 else 0.0
            tot_s = (tot / fps) if fps > 0 else 0.0
            self.yt_time_label.setText(f"{fmt(cur)} / {fmt(tot_s)}")
        except Exception:
            pass  

    def _update_player_button_sizes(self):
        # Define tamanhos a partir de uma largura fixa da barra do player
        try:
            container_w = int(getattr(self, '_player_controls_fixed_width', 600))
        except Exception:
            container_w = 600
        small_w = max(44, min(60, int(container_w * 0.09)))
        medium_w = max(96, min(128, int(container_w * 0.22)))
        btn_h = max(32, min(40, int(container_w * 0.07)))

        for btn in [getattr(self, 'prev_frame_btn', None), getattr(self, 'next_frame_btn', None), getattr(self, 'fullscreen_btn', None)]:
            if btn:
                btn.setFixedWidth(small_w)
                btn.setFixedHeight(btn_h)
                btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        for btn in [getattr(self, 'play_pause_btn', None), getattr(self, 'annotate_btn', None)]:
            if btn:
                btn.setMinimumWidth(medium_w)
                btn.setMaximumWidth(medium_w)
                btn.setFixedHeight(btn_h)
                btn.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        if hasattr(self, 'speed_combo') and self.speed_combo:
            self.speed_combo.setFixedHeight(max(24, btn_h - 6))

    def _arm_annotation(self):
        self.annotation_arm = True
        self._pause_analysis()
        if hasattr(self, 'status_label'):
            self.status_label.setText("Clique no vídeo para marcar e comentar")

    def _on_slider_pressed(self):
        self._seeking = True
        self._pause_analysis()

    def _on_slider_released(self):
        self._seeking = False
        idx = int(self.frame_slider.value()) if hasattr(self, 'frame_slider') else 0
        self._seek_to_frame(idx)

    def _on_slider_changed(self, value):
        if hasattr(self, 'frame_info_label'):
            self.frame_info_label.setText(
                f"Frame: {int(value)}/{max(0, self.total_frames - 1)}")
        # Se não estiver tocando, renderiza imediatamente ao arrastar
        if not self.timer.isActive() and not self._seeking:
            self._seek_to_frame(int(value))

    def _change_speed(self, text):
        try:
            spd = float(text.replace('x', '').strip())
        except Exception:
            spd = 1.0
        self.playback_speed = max(0.25, spd)
        if self.timer.isActive():
            self.timer.setInterval(compute_interval_ms(self.base_interval_ms, self.playback_speed))

    def _seek_to_frame(self, index):
        if not self.cap or self.total_frames <= 0:
            return
        idx = clamp_frame_index(index, self.total_frames)
        try:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        except Exception:
            pass
        ok, frame = self.cap.read()
        if not ok:
            return
        # Garantir que mostramos exatamente o idx
        try:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        except Exception:
            pass
        self.current_frame_index = idx
        target_w = (self.video_display.width() if hasattr(self, 'video_display') else self.video_label.width())
        target_h = (self.video_display.height() if hasattr(self, 'video_display') else self.video_label.height())
        frame = self._fit_frame_to_label(frame)
        frame = self._analyze_frame(frame)
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        target_size = (self.video_display.size() if hasattr(self, 'video_display') else self.video_label.size())
        scaled = pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if hasattr(self, 'video_display'):
            self.video_display.setPixmap(scaled)
        else:
            self.video_label.setPixmap(scaled)
        if hasattr(self, 'frame_slider'):
            bs = self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(idx)
            self.frame_slider.blockSignals(bs)
        if hasattr(self, 'yt_bar'):
            try:
                self.yt_bar.setValue(idx)
            except Exception:
                pass
        if hasattr(self, 'frame_info_label'):
            self.frame_info_label.setText(f"Frame: {idx}/{max(0, self.total_frames - 1)}")
        if hasattr(self, 'yt_time_label'):
            self._update_time_label()

    def _step_frame(self, delta):
        self._pause_analysis()
        new_idx = clamp_frame_index(self.current_frame_index + int(delta), self.total_frames)
        self._seek_to_frame(new_idx)

    def _toggle_play_pause(self):
        if self.timer.isActive():
            self._pause_analysis()
        else:
            self._start_analysis()
        if hasattr(self, 'yt_time_label'):
            self._update_time_label()

    def _fit_frame_to_label(self, frame):
        try:
            lh = (self.video_display.height() if hasattr(self, 'video_display') else self.video_label.height())
            lw = (self.video_display.width() if hasattr(self, 'video_display') else self.video_label.width())
            if lw <= 0 or lh <= 0:
                return frame
            h, w = frame.shape[:2]
            if h <= 0 or w <= 0:
                return frame
            ratio = w / float(h)
            target_w = int(min(lw, lh * ratio))
            target_h = int(target_w / ratio)
            resized = cv2.resize(frame, (max(1, target_w), max(1, target_h)))
            canvas = np.zeros((max(1, lh), max(1, lw), 3), dtype=np.uint8)
            off_x = max(0, (lw - target_w) // 2)
            off_y = max(0, (lh - target_h) // 2)
            canvas[off_y:off_y+target_h, off_x:off_x+target_w] = resized
            return canvas
        except Exception:
            return frame

    def _toggle_fullscreen(self):
        try:
            self.is_fullscreen = not getattr(self, 'is_fullscreen', False)
            if self.is_fullscreen:
                self.showFullScreen()
                if hasattr(self, 'fullscreen_btn'):
                    self.fullscreen_btn.setText("⤡")
                    self.fullscreen_btn.setToolTip("Sair da tela cheia")
            else:
                self.showNormal()
                if hasattr(self, 'fullscreen_btn'):
                    self.fullscreen_btn.setText("⤢")
                    self.fullscreen_btn.setToolTip("Tela cheia")
            # Reajusta área de vídeo e controles
            self._resize_video_area()
            self._update_player_controls_width()
            self._update_player_button_sizes()
        except Exception:
            pass

    def _reset_counters(self):
        self.rep_count = 0
        self.rep_label.setText("Repetições: 0")
        self.history_tree.clear()
        if hasattr(self, 'yt_time_label'):
            self._update_time_label()

    def _update_frame(self):
        if not self.cap:
            return

        ret, frame = self.cap.read()
        if not ret:
            self.timer.stop()
            if self.cap:
                self.cap.release()
                self.cap = None
            if hasattr(self, 'play_pause_btn'):
                self.play_pause_btn.setText("► Iniciar")
            if hasattr(self, 'status_label'):
                self.status_label.setText("Sem vídeo")
            if hasattr(self, 'yt_bar'):
                try:
                    self.yt_bar.setValue(self.current_frame_index)
                except Exception:
                    pass
            if hasattr(self, 'yt_time_label'):
                self._update_time_label()
            return

        # Atualiza índice de frame atual
        try:
            pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1
            self.current_frame_index = clamp_frame_index(pos, self.total_frames)
        except Exception:
            self.current_frame_index = max(0, self.current_frame_index + 1)

        # Redimensionar o frame para o tamanho atual do label
        target_w = (self.video_display.width() if hasattr(self, 'video_display') else self.video_label.width())
        target_h = (self.video_display.height() if hasattr(self, 'video_display') else self.video_label.height())
        frame = self._fit_frame_to_label(frame)

        frame = self._analyze_frame(frame)

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        img = QImage(frame_rgb.data, w, h,
                     bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(img)
        # Ajustar o vídeo ao tamanho atual do label mantendo proporção
        target_size = (self.video_display.size() if hasattr(self, 'video_display') else self.video_label.size())
        scaled = pixmap.scaled(target_size,
                               Qt.KeepAspectRatio, Qt.SmoothTransformation)
        if hasattr(self, 'video_display'):
            self.video_display.setPixmap(scaled)
        else:
            self.video_label.setPixmap(scaled)
        # Sincroniza slider e rótulo de frame
        if hasattr(self, 'frame_slider'):
            bs = self.frame_slider.blockSignals(True)
            self.frame_slider.setValue(self.current_frame_index)
            self.frame_slider.blockSignals(bs)
        if hasattr(self, 'yt_bar'):
            try:
                self.yt_bar.setValue(self.current_frame_index)
            except Exception:
                pass
        if hasattr(self, 'frame_info_label'):
            self.frame_info_label.setText(
                f"Frame: {self.current_frame_index}/{max(0, self.total_frames - 1)}")
        if hasattr(self, 'yt_time_label'):
            self._update_time_label()

    def _load_athletes_on_click(self, event):
        """Carrega lista de atletas quando clica no combo"""
        # Primeiro executa o comportamento normal do combo
        self.athlete_combo.showPopup()
        
        # Se está vazio ou só tem o placeholder, carrega a lista
        current_text = self.athlete_combo.currentText()
        if (self.athlete_combo.count() <= 1 or 
            current_text == "Clique para carregar atletas..." or
            current_text == "Selecione ou digite..." or
            "carregar atletas" in current_text.lower()):
            self._refresh_athletes_combo()

    def _refresh_athletes_combo(self):
        """Atualiza o combo com atletas do histórico"""
        try:
            print("🔄 Buscando atletas do banco...")
            
            # Salva o texto atual
            current_text = self.athlete_combo.currentText()
            
            # Limpa o combo
            self.athlete_combo.clear()
            
            # Busca atletas do histórico
            athletes = self._load_athletes_from_history()
            
            print(f"📊 {len(athletes)} atletas encontrados:")
            for athlete in athletes:
                print(f"   - {athlete}")
            
            if athletes:
                self.athlete_combo.addItems(athletes)
                if current_text and current_text in athletes:
                    self.athlete_combo.setCurrentText(current_text)
                else:
                    self.athlete_combo.setCurrentIndex(0)
            else:
                self.athlete_combo.addItem("Nenhum atleta encontrado")
                self.athlete_combo.setCurrentIndex(0)
                
            # Atualiza autocompletar
            if hasattr(self.athlete_combo, 'completer') and athletes:
                model = QStringListModel(athletes)
                self.athlete_combo.completer().setModel(model)
                
        except Exception as e:
            print(f"❌ Erro ao carregar atletas: {e}")
            import traceback
            traceback.print_exc()
            self.athlete_combo.addItem("Erro ao carregar")
            
            
    def _load_athletes_from_history(self):
        """Busca nomes de atletas do histórico"""
        athletes = set()
        
        try:
            # Tenta buscar do banco de dados
            from storage.persistence import fetch_attempts
            records = fetch_attempts(limit=1000)
            for rec in records:
                athlete = rec.get('athlete', '').strip()
                if athlete and athlete not in ['', 'Atleta']:
                    athletes.add(athlete)
        except Exception:
            pass
        
        try:
            # Fallback para arquivo CSV
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            csv_path = os.path.join(base, 'storage', 'historico.csv')
            if os.path.exists(csv_path):
                import pandas as pd
                df = pd.read_csv(csv_path)
                if 'Atleta' in df.columns:
                    for athlete in df['Atleta'].dropna().unique():
                        athlete_str = str(athlete).strip()
                        if athlete_str and athlete_str not in ['', 'Atleta']:
                            athletes.add(athlete_str)
        except Exception:
            pass
        
        # Adiciona atletas da lista salva também
        try:
            saved_athletes = self._load_athlete_list()
            for athlete in saved_athletes:
                if athlete.strip() and athlete not in ['', 'Atleta']:
                    athletes.add(athlete.strip())
        except Exception:
            pass
        
        return sorted(list(athletes))
        
def main():
    app = QApplication(sys.argv)
    window = VideoAnalysisApp("")
    window.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
