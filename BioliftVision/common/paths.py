import os
import sys


def app_root() -> str:
    # Retorna a raiz do projeto (pai de 'common/')
    return os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))


def models_dir() -> str:
    # Novo diretório padronizado para modelos
    return os.path.join(app_root(), 'model')


def model_file() -> str:
    # Novo arquivo padronizado do modelo
    new_path = os.path.join(models_dir(), 'model.pkl')
    if os.path.exists(new_path):
        return new_path
    # Fallback para compatibilidade com modelos antigos
    legacy_path = os.path.join(app_root(), 'models_oneclass', 'powerlifting_model.joblib')
    if os.path.exists(legacy_path):
        return legacy_path
    # Caso nenhum exista, retornar o novo caminho por padrão
    return new_path


def logs_dir() -> str:
    return os.path.join(app_root(), 'logs')


def results_dir() -> str:
    return os.path.join(app_root(), 'results_oneclass')


def resource_path(relative_path: str) -> str:
    """Retorna caminho compatível com execução normal e PyInstaller."""
    base = getattr(sys, "_MEIPASS", app_root())
    return os.path.join(base, relative_path)
