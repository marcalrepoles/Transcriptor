def format_timestamp(seconds: float, milliseconds: bool = False) -> str:
    seconds = max(0.0, float(seconds))
    whole = int(seconds)
    hours, remainder = divmod(whole, 3600)
    minutes, secs = divmod(remainder, 60)
    base = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    if milliseconds:
        return f"{base}.{int((seconds - whole) * 1000):03d}"
    return base

