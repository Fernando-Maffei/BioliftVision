import sys
import importlib.util
from importlib import metadata
from packaging.version import Version
from common.logger import log_info, log_warning
from common.paths import app_root
from pathlib import Path

REQUIRED = {
    'numpy': None,
    'opencv-python': 'cv2',
    'mediapipe': None,
    'pandas': None,
    'pyarrow': None,
}

MIN_VERSIONS = {
    'numpy': Version('1.24.0'),
    'opencv-python': Version('4.8.0'),
    'mediapipe': Version('0.10.0'),
    'pandas': Version('2.0.0'),
    'pyarrow': Version('12.0.0'),
}


def _load_min_versions_from_requirements():
    """Lê config/requirements.txt e atualiza MIN_VERSIONS com especificadores 
    'package>=version' ou 'package==version' se presentes."""
    try:
        req_path = Path(app_root()) / 'config' / 'requirements.txt'
        if not req_path.exists():
            return
        for line in req_path.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            # Suporta 'pkg>=1.2.3' e 'pkg==1.2.3'
            for sep in ('>=', '=='):
                if sep in line:
                    try:
                        pkg, ver = [p.strip() for p in line.split(sep, 1)]
                        # mantém apenas pacotes de interesse
                        if pkg in REQUIRED:
                            MIN_VERSIONS[pkg] = Version(ver)
                    except Exception:
                        pass
                    break
    except Exception:
        # silencioso
        pass


def in_venv() -> bool:
    return sys.prefix != getattr(sys, 'base_prefix', sys.prefix)


def check_packages() -> list:
    problems = []
    # Atualiza min versions com requirements.txt, se disponível
    _load_min_versions_from_requirements()
    for dist_name, import_name in REQUIRED.items():
        # Checa presença do pacote sem importá-lo
        spec_present = importlib.util.find_spec(
            import_name or dist_name) is not None
        try:
            installed_ver = Version(metadata.version(dist_name))
        except metadata.PackageNotFoundError:
            installed_ver = None

        if not spec_present or installed_ver is None:
            problems.append(f"Pacote ausente: {dist_name}")
            continue

        minv = MIN_VERSIONS.get(dist_name)
        if minv and installed_ver < minv:
            problems.append(
                f"{dist_name} versão {installed_ver} < mínima {minv}")
    return problems


def print_summary():
    log_info("=== Verificação de Ambiente ===")
    log_info(f"Python: {sys.version.split()[0]}")
    log_info(f"Venv ativa: {'SIM' if in_venv() else 'NÃO'}")
    issues = check_packages()
    if issues:
        log_warning("Problemas detectados:")
        for i in issues:
            log_warning(f" - {i}")
        log_warning(
            "Sugestão: ative a venv e rode `python -m pip install -r config/requirements.txt`.")
    else:
        log_info("Ambiente OK.")
