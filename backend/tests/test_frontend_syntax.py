"""Front-end JS fayllari sintaksis jihatdan to'g'rimi (node bo'lsa). Bitta faylda xato bo'lsa, butun bo'lim ochilmaydi —
2026-10-13 da shunday xato serverga chiqib ketgan edi (pages-fin.js, qo'shtirnoq)."""

import shutil
import subprocess
from pathlib import Path

import pytest

JS = Path(__file__).resolve().parents[2] / "frontend" / "assets" / "js"
NODE = shutil.which("node")


@pytest.mark.skipif(NODE is None or not JS.exists(), reason="node yoki frontend/ yo'q (masalan, Docker obrazida)")
@pytest.mark.parametrize("path", sorted(JS.glob("*.js")) if JS.exists() else [], ids=lambda p: p.name)
def test_js_parses(path):
    code = "new Function(require('fs').readFileSync(process.argv[1], 'utf8'))"
    r = subprocess.run([NODE, "-e", code, str(path)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr[-800:]
