import os
import sys
import json
import argparse
from pathlib import Path
import subprocess
import pandas as pd
_base_dir = os.path.dirname(os.path.abspath(__file__))
_proj_root = os.path.abspath(os.path.join(_base_dir, '..'))
if _proj_root not in sys.path:
    sys.path.insert(0, _proj_root)
from common.logger import log_info, log_warning, log_error
from common.paths import app_root
from core.keypoints import process_correct_movements

def _list_videos(dirp: Path) -> list[Path]:
    exts = ("*.mp4", "*.avi", "*.mov", "*.mkv")
    vids: list[Path] = []
    for e in exts:
        vids.extend(dirp.rglob(e))
    return vids

def extract_video_metadata(input_dir: Path, out_csv: Path, out_json: Path) -> pd.DataFrame:
    rows = []
    files = _list_videos(input_dir)
    for vp in files:
        try:
            size_mb = vp.stat().st_size / (1024*1024)
            dur = 0.0
            w = 0
            h = 0
            fps = 0.0
            try:
                r = subprocess.run([
                    "ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_format", "-show_streams", str(vp)
                ], capture_output=True, text=True, timeout=8)
                if r.returncode == 0:
                    info = json.loads(r.stdout)
                    fmt = info.get("format", {})
                    dur = float(fmt.get("duration", 0.0)) if fmt else 0.0
                    for s in info.get("streams", []):
                        if s.get("codec_type") == "video":
                            w = int(s.get("width", 0))
                            h = int(s.get("height", 0))
                            fr = s.get("r_frame_rate")
                            if isinstance(fr, str) and "/" in fr:
                                num, den = fr.split("/")
                                fps = float(num) / float(den) if float(den) != 0 else 0.0
                            break
            except Exception:
                pass
            if dur == 0.0:
                try:
                    import cv2
                    cap = cv2.VideoCapture(str(vp))
                    if cap.isOpened():
                        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        fps = float(cap.get(cv2.CAP_PROP_FPS))
                        fc = float(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                        if fps > 0 and fc > 0:
                            dur = fc / fps
                        cap.release()
                except Exception:
                    pass
            ar = (w/float(h)) if h > 0 else 0.0
            mp = (w*h)/1_000_000.0 if w > 0 and h > 0 else 0.0
            rows.append({
                "video_path": str(vp),
                "filename": vp.name,
                "file_size_mb": size_mb,
                "duration_seconds": dur,
                "width": w,
                "height": h,
                "fps": fps,
                "aspect_ratio": ar,
                "megapixels": mp,
            })
        except Exception as e:
            log_warning(f"Falha ao analisar {vp}: {e}")
    df = pd.DataFrame(rows)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_csv(out_csv, index=False)
        with open(out_json, "w", encoding="utf-8") as fh:
            json.dump(rows, fh, ensure_ascii=False, indent=2)
        log_info(f"Metadados salvos: {out_csv}")
    except Exception as e:
        log_warning(f"Falha ao salvar metadados: {e}")
    return df

def run_training_pipeline(input_dir: Path | None):
    base = Path(app_root())
    if input_dir and not input_dir.exists():
        log_warning("Diretório de entrada não existe; usando dataset local")
        input_dir = None
    dataset_file = None
    if input_dir:
        out_dir = base / "dataset" / "processed_oneclass"
        df = process_correct_movements(str(input_dir), str(out_dir))
        if not df.empty:
            dataset_file = str((out_dir / "correct_movements.parquet").resolve())
        else:
            log_warning("Nenhum vídeo processado; usando dataset local")
    args = ["train_model.py"]
    if dataset_file:
        args += ["--dataset-file", dataset_file]
    try:
        from core.train_model import main as train_main
        bak = list(sys.argv)
        sys.argv = args
        try:
            train_main()
        finally:
            sys.argv = bak
    except Exception as e:
        log_error(f"Falha no treinamento: {e}")
        raise

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir")
    opts = ap.parse_args()
    d = Path(opts.input_dir) if opts.input_dir else None
    run_training_pipeline(d)

if __name__ == "__main__":
    main()