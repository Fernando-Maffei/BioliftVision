from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QColor, QGuiApplication, QIcon
from PyQt5.QtWidgets import QApplication, QSplashScreen, QMessageBox
from ui.style import get_global_styles, apply_theme
from ui import style as ui_style
import sys
import os
import subprocess
from common.logger import log_info, log_error, log_warning
from common.paths import resource_path, model_file
from pathlib import Path
import json
import time
import warnings

warnings.filterwarnings(
    'ignore',
    message=r'.*SymbolDatabase\.GetPrototype\(\).*',
    category=UserWarning
)
warnings.filterwarnings(
    'ignore',
    category=UserWarning,
    module='google.protobuf.symbol_database'
)

try:
    from core.run_model import ensure_model_ready, latest_model_info
except Exception:
    ensure_model_ready = None
    latest_model_info = None


class PowerliftingApp:
    def start(self):
        """Inicia a aplicação com a tela de login"""
        try:
            log_info("Iniciando aplicação Powerlifting Analysis System")
            # Windows: definir AppUserModelID para agrupar e permitir ícone próprio na barra
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "PowerliftingAnalysis.PowerliftingApp")
            except Exception:
                pass
            # Checagem inicial de modelo e dependências
            try:
                cfg_path = Path(os.path.dirname(os.path.abspath(
                    __file__))) / 'config' / 'pipeline.json'
                auto_load = True
                if cfg_path.exists():
                    with open(cfg_path, 'r', encoding='utf-8') as fh:
                        cfg = json.load(fh)
                    auto_load = bool(cfg.get('integration', {}).get(
                        'auto_load_on_start', True))
                if ensure_model_ready and auto_load:
                    ok, err = ensure_model_ready()
                    if not ok:
                        log_warning(f"Modelo não pronto no início: {err}")
                    else:
                        if latest_model_info:
                            info = latest_model_info()
                            if info:
                                log_info(
                                    f"Último modelo: {info.get('path')} (criado em {info.get('created_at')})")
            except Exception:
                pass

            app = QApplication(sys.argv)
            try:
                # Definir ícone global do app preferindo icon_hotbar
                from PyQt5.QtGui import QPixmap
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
                    app.setWindowIcon(QIcon(ico_path))
                else:
                    app.setWindowIcon(QIcon(png_path))
            except Exception:
                pass

            # Feedback de espera durante bootstrap
            try:
                QApplication.setOverrideCursor(Qt.WaitCursor)
            except Exception:
                pass

            # Tema e estilos globais
            os.environ.setdefault('POWERLIFT_THEME', 'AuroraDark')
            apply_theme(os.environ.get('POWERLIFT_THEME', 'AuroraDark'))
            app.setStyle('Fusion')
            app.setStyleSheet(get_global_styles())

            # Splash de carregamento
            try:
                from ui.splash import SplashDialog
                splash = SplashDialog()
                splash.set_message("Carregando recursos...")
                splash.set_progress(5)
                splash.show()
                app.processEvents()
                splash_start = time.monotonic()
                # Pré-carregar imagem de fundo para evitar flicker na transição
                try:
                    bg = QPixmap(resource_path('ui/background.png'))
                    if not bg.isNull():
                        setattr(app, '_biolift_bg_pixmap', bg)
                except Exception:
                    pass
            except Exception:
                splash = None

            # Usar telas separadas via reexports do pacote ui
            try:
                from ui import LoginWindow, MainMenu
                self._LoginWindowClass = LoginWindow
                self._MainMenuClass = MainMenu
            except Exception as e:
                log_error(f"Falha ao importar UI (Login/MainMenu): {e}")
                try:
                    QMessageBox.critical(None, "Erro de inicialização",
                                         f"Falha ao carregar componentes da interface.\n\nDetalhes: {e}\n\n"
                                         "Verifique se as dependências estão instaladas corretamente.")
                except Exception:
                    pass
                raise
            # Bootstrap com etapas e feedback visual
            try:
                db_ok = True
                if splash:
                    splash.set_message("Preparando o software...")
                    splash.set_progress(10)
                # Etapa: modelo
                try:
                    if ensure_model_ready:
                        ok, err = ensure_model_ready()
                        if splash:
                            splash.set_message("Modelo pronto" if ok else "Verificando modelo...")
                            splash.set_progress(35)
                except Exception:
                    if splash:
                        splash.set_message("Modelo: passo ignorado")
                        splash.set_progress(35)
                # Etapa: banco
                try:
                    from db.user_repository import UserRepository
                    repo = UserRepository()
                    _ok_tbl = repo.ensure_users_table()
                    repo.close()
                    db_ok = bool(_ok_tbl)
                    if splash:
                        splash.set_message("Banco disponível" if _ok_tbl else "Banco indisponível")
                        splash.set_progress(60)
                except Exception:
                    db_ok = False
                    if splash:
                        splash.set_message("Banco: passo ignorado")
                        splash.set_progress(60)
                # Etapa: recursos
                try:
                    needed = [
                        resource_path('ui/background.png'),
                        resource_path('ui/icon_app.png'),
                        resource_path('ui/tela_loading.png'),
                    ]
                    missing = [p for p in needed if not os.path.exists(p)]
                    if splash:
                        splash.set_message("Recursos OK" if not missing else "Faltam recursos")
                        splash.set_progress(80)
                except Exception:
                    if splash:
                        splash.set_message("Recursos: passo ignorado")
                        splash.set_progress(80)
                # Etapa final
                if splash:
                    splash.set_message("Abrindo a aplicação...")
                    splash.set_progress(100)
            except Exception:
                pass

            # Garantir exibição mínima da splash (configurável via POWERLIFT_SPLASH_MIN_SECONDS)
            try:
                if splash:
                    min_seconds = float(os.environ.get('POWERLIFT_SPLASH_MIN_SECONDS', '6'))
                    elapsed = time.monotonic() - (splash_start if 'splash_start' in locals() else time.monotonic())
                    remaining = max(0.0, min_seconds - elapsed)
                    if remaining > 0:
                        tps = float(os.environ.get('POWERLIFT_SPLASH_TICKS_PER_SEC', '3'))
                        steps = max(5, int(remaining * tps))
                        base = splash.progress.value() if hasattr(splash, 'progress') else 95
                        for i in range(steps):
                            try:
                                pct = min(100, base + int((100 - base) * (i + 1) / steps))
                                if hasattr(splash, 'set_progress'):
                                    splash.set_progress(pct)
                                if hasattr(splash, 'set_message'):
                                    splash.set_message("Carregando recursos...")
                                app.processEvents()
                            except Exception:
                                pass
                            time.sleep(remaining / steps)
            except Exception:
                pass

            self.show_login()

            # Aviso se banco estiver indisponível
            try:
                if not db_ok:
                    QMessageBox.warning(None, "Banco de dados",
                                        "Não foi possível conectar ao banco de dados.\n"
                                        "Verifique o ODBC Driver 17, credenciais e o SQL Server.\n\n"
                                        "A aplicação abrirá normalmente, mas funções que dependem do banco podem ficar limitadas.")
            except Exception:
                pass

            # Fechar splash
            if splash:
                try:
                    splash.close()
                except Exception:
                    pass
            try:
                QApplication.restoreOverrideCursor()
            except Exception:
                pass
            sys.exit(app.exec_())
        except Exception as e:
            log_error(f"Erro crítico na aplicação principal: {str(e)}")
            raise

    def show_login(self):
        log_info("Exibindo tela de login")
        self.login_window = self._LoginWindowClass(parent=self)
        self.login_window.setMinimumSize(960, 640)
        # Tentar maximizar; se falhar ou não aparecer, fazer fallback para show()
        try:
            self.login_window.showMaximized()
        except Exception:
            try:
                self.login_window.show()
            except Exception:
                pass
        # Garantir que a janela venha para frente e seja ativada
        try:
            self.login_window.raise_()
            self.login_window.activateWindow()
        except Exception:
            pass
        # Processar eventos iniciais para evitar atraso de renderização
        try:
            from PyQt5.QtWidgets import QApplication as _QA
            app = _QA.instance()
            if app:
                app.processEvents()
        except Exception:
            pass
        # Guard: se por algum motivo não estiver visível após ~800ms, reexibir
        try:
            QTimer.singleShot(800, self._ensure_login_visible)
        except Exception:
            pass
        # Pré-aquecer o menu principal em background para acelerar a transição
        try:
            self._prewarmed_main_menu = None
            QTimer.singleShot(50, self._prewarm_main_menu)
        except Exception:
            self._prewarmed_main_menu = None

    def show_main_menu(self):
        log_info("Exibindo menu principal")
        if getattr(self, 'login_window', None):
            try:
                self.login_window.close()
            except Exception:
                pass
            self.login_window = None
        # Reaproveita instância pré-aquecida se disponível
        try:
            if hasattr(self, '_prewarmed_main_menu') and self._prewarmed_main_menu is not None:
                self.main_menu = self._prewarmed_main_menu
                self._prewarmed_main_menu = None
            else:
                self.main_menu = self._MainMenuClass()
        except Exception:
            self.main_menu = self._MainMenuClass()
        # Atualiza a visibilidade de controles administrativos após saber quem logou
        try:
            if hasattr(self.main_menu, 'refresh_admin_visibility'):
                self.main_menu.refresh_admin_visibility()
        except Exception:
            pass
        try:
            self.main_menu.showMaximized()
        except Exception:
            self.main_menu.show()
        # Agenda verificação de ambiente em background, evitando bloquear startup
        try:
            pass
        except Exception:
            pass

    def _prewarm_main_menu(self):
        """Cria a janela de menu principal antecipadamente para reduzir tempo de abertura."""
        try:
            if not hasattr(self, '_prewarmed_main_menu') or self._prewarmed_main_menu is None:
                self._prewarmed_main_menu = self._MainMenuClass()
        except Exception:
            self._prewarmed_main_menu = None

    def _ensure_login_visible(self):
        try:
            if hasattr(self, 'login_window') and self.login_window is not None:
                if not self.login_window.isVisible():
                    log_warning(
                        "Janela de login não estava visível. Reexibindo.")
                    try:
                        self.login_window.show()
                        self.login_window.raise_()
                        self.login_window.activateWindow()
                    except Exception:
                        pass
                # Se estiver minimizada ou fora da tela, centralizar e restaurar
                try:
                    # Restaurar se minimizada
                    if self.login_window.isMinimized():
                        self.login_window.showNormal()
                    # Centralizar na tela primária
                    screen = QGuiApplication.primaryScreen()
                    if screen is not None:
                        geo = screen.availableGeometry()
                        win_geo = self.login_window.frameGeometry()
                        win_geo.moveCenter(geo.center())
                        self.login_window.move(win_geo.topLeft())
                    # Garantir foco e topo
                    self.login_window.raise_()
                    self.login_window.activateWindow()
                except Exception:
                    pass
        except Exception:
            pass


def main():
    """Função principal - ponto de entrada da aplicação"""
    

    # Se chamado com --analysis, inicia diretamente a interface de análise
    if "--analysis" in sys.argv:
        try:
            from ui.interface import VideoAnalysisApp
            log_info("Iniciando modo análise")
            # Configuração de conexão MSSQL (usa env vars; não sobrescreve se já definidas)
            try:
                os.environ.setdefault("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
                # Ajuste servidor/banco conforme ambiente do projeto
                os.environ.setdefault("MSSQL_SERVER", r"localhost")
                os.environ.setdefault("MSSQL_DB", "bioliftvisionDB")
                os.environ.setdefault("MSSQL_USER", "sa")
                os.environ.setdefault("MSSQL_PASSWORD", "")
                # Se preferir conexão confiável do Windows, marque MSSQL_TRUSTED=true
                os.environ.setdefault("MSSQL_TRUSTED", "false")
                # Seleciona automaticamente o driver disponível instalado
                try:
                    import pyodbc  # type: ignore
                    available = [d.strip() for d in pyodbc.drivers()]
                    preferred = None
                    for cand in ("ODBC Driver 18 for SQL Server", "ODBC Driver 17 for SQL Server", "SQL Server"):
                        if cand in available:
                            preferred = cand
                            break
                    if preferred:
                        os.environ["MSSQL_DRIVER"] = preferred
                except Exception:
                    pass
                # Inicializa schema das tabelas se necessário
                try:
                    from db.analysis_repository import AnalysisRepository
                    repo = AnalysisRepository()
                    # Tenta criar tabelas base e procedimento utilitário
                    repo.create_schema()
                except Exception as e:
                    log_warning(f"Não foi possível inicializar schema do banco: {e}")
            except Exception:
                pass
            # Definir AppUserModelID para o processo (ícone correto na barra de tarefas)
            try:
                import ctypes
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "PowerliftingAnalysis.PowerliftingApp")
            except Exception:
                pass
            # Caminho do modelo treinado (carregamento silencioso)
            model_path = model_file()
            if not os.path.exists(model_path):
                # Carregar em modo visual sem modelo
                log_warning(
                    f"Modelo não encontrado em '{model_path}'. Iniciando apenas análise visual.")
                model_path = ""

            app = QApplication(sys.argv)
            try:
                # Ícone global no modo análise
                from PyQt5.QtGui import QPixmap
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
                    app.setWindowIcon(QIcon(ico_path))
                else:
                    app.setWindowIcon(QIcon(png_path))
            except Exception:
                pass
            # Tema e estilos globais
            os.environ.setdefault('POWERLIFT_THEME', 'AuroraDark')
            apply_theme(os.environ.get('POWERLIFT_THEME', 'AuroraDark'))
            app.setStyle('Fusion')
            app.setStyleSheet(get_global_styles())

            window = VideoAnalysisApp(model_path)
            # Abrir em tela inteira para aproveitar toda a área útil
            try:
                window.showFullScreen()
            except Exception:
                try:
                    window.showMaximized()
                except Exception:
                    window.show()
            sys.exit(app.exec_())
            return
        except Exception as e:
            # Tratamento robusto: informar ao usuário e fazer fallback para app padrão
            log_error(f"Falha ao iniciar modo análise: {e}")
            try:
                QMessageBox.critical(None, "Erro ao iniciar análise",
                                     "O modo de análise não pôde ser iniciado.\n\n"
                                     f"Detalhes: {e}\n\n"
                                     "Possíveis causas:\n"
                                     "- 'mediapipe' não instalado ou incompatível com seu Python.\n"
                                     "- Falta do Microsoft Visual C++ Redistributable (x64).\n"
                                     "- Incompatibilidade de versões do 'numpy/protobuf'.\n\n"
                                     "A aplicação continuará em modo padrão (login/menu).")
            except Exception:
                pass
            # Em vez de abortar, iniciar app padrão
            app_controller = PowerliftingApp()
            app_controller.start()
            return

    # Se chamado com --training, executa o pipeline de treinamento
    elif "--training" in sys.argv:
        try:
            log_info("Iniciando modo treinamento")
            try:
                from core.train_model import main as train_main
                _args_bak = list(sys.argv)
                _extra: list[str] = []
                for i, a in enumerate(_args_bak):
                    if a == "--input-dir":
                        _extra.append(a)
                        if i + 1 < len(_args_bak):
                            _extra.append(_args_bak[i + 1])
                sys.argv = ["train_model.py"] + _extra
                try:
                    train_main()
                finally:
                    sys.argv = _args_bak
                return
            except Exception as e:
                log_error(f"Falha no treinamento: {e}")
                try:
                    QMessageBox.critical(None, "Treinamento", f"Falha ao executar treinamento.\n\nDetalhes: {e}")
                except Exception:
                    pass
        except Exception:
            pass

    app_controller = PowerliftingApp()
    app_controller.start()


if __name__ == "__main__":
    main()
