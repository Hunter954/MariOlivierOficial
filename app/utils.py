def format_seconds_to_progress(seconds: int, total_minutes: int) -> int:
    total_seconds = max(total_minutes * 60, 1)
    return min(int((seconds / total_seconds) * 100), 100)
