def compute_interval_ms(base_interval_ms: int, speed: float) -> int:
    try:
        speed_eff = max(0.25, float(speed))
        base = int(base_interval_ms) if base_interval_ms and base_interval_ms > 0 else 33
        return max(5, int(base / speed_eff))
    except Exception:
        return 33


def clamp_frame_index(index: int, total_frames: int) -> int:
    """Garante que o índice de frame esteja dentro de [0, total_frames-1]."""
    try:
        if total_frames <= 0:
            return 0
        return max(0, min(int(index), int(total_frames) - 1))
    except Exception:
        return 0
