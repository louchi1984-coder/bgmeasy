"""Load librosa with a private temporary JIT cache if its default locations fail."""
from pathlib import Path
import tempfile

import librosa
from numba import config

# Numba can silently fall back from a bad explicit path to a different location.
config.reload_config()
if config.CACHE_DIR:
    try:
        Path(config.CACHE_DIR).mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=config.CACHE_DIR):
            pass
    except OSError as error:
        raise RuntimeError(f'Set NUMBA_CACHE_DIR to a writable directory '
                           f'(current: {config.CACHE_DIR}): {error}') from error

# Importing librosa alone does not load its Numba-decorated pitch conversions.
try:
    librosa.midi_to_hz(69)
except RuntimeError as error:
    if 'cannot cache function' not in str(error) or 'no locator available' not in str(error):
        raise
    if config.CACHE_DIR:
        raise RuntimeError(f'{error}. Set NUMBA_CACHE_DIR to a writable directory '
                           f'(current: {config.CACHE_DIR}).') from error
    try:
        # Keep it alive while later librosa operations compile other functions.
        _private_cache = tempfile.TemporaryDirectory(prefix='bgmeasy-numba-')
    except OSError as cause:
        raise RuntimeError(f'Set NUMBA_CACHE_DIR to a writable directory. '
                           f'Unable to create a temporary cache: {cause}') from cause
    config.CACHE_DIR = _private_cache.name
    librosa.midi_to_hz(69)
