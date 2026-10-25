#!/usr/bin/env bash
# Foydalanish: bash run.sh rec 01 02   (TV_COPY_DIR — nusxa baza papkasi)
cd "$(dirname "$0")"
export PYTHONIOENCODING=utf-8
export TV_COPY_DIR="${TV_COPY_DIR:-C:/Users/SURFAC~1/AppData/Local/Temp/claude/D--wibecoding-codialERP1/27703410-1de5-43e2-a1e2-29043cbd1903/scratchpad/copy}"
exec .venv/Scripts/python make.py "$@"
