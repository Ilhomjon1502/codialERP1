"""Barcha darslar (Administrator+Hisobchi uchun yo'riqnoma). Har bir dars — l<NN>.py faylida."""
import importlib
from pathlib import Path

from common import LESSONS

for _p in sorted(Path(__file__).parent.glob("l[0-9][0-9].py")):
    importlib.import_module(_p.stem)

__all__ = ["LESSONS"]
