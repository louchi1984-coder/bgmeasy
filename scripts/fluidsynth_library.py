"""Locate FluidSynth beside its CLI as well as through the system loader."""
import ctypes.util
from pathlib import Path
import shutil


def find_library():
    found = ctypes.util.find_library('fluidsynth')
    if found:
        return found
    cli = shutil.which('fluidsynth')
    if not cli:
        return None
    binary = Path(cli).resolve().parent
    for folder in (binary, binary.parent/'lib'):
        for name in ('libfluidsynth-3.dll', 'libfluidsynth-2.dll', 'fluidsynth.dll',
                     'libfluidsynth.dylib', 'libfluidsynth.so.3', 'libfluidsynth.so.2'):
            candidate = folder/name
            if candidate.is_file():
                return str(candidate)
    return None
