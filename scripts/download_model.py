"""
Baixa o modelo YOLOX Nano no formato ONNX direto do release oficial
do projeto no GitHub (Megvii-BaseDetection/YOLOX) e salva em
models/yolox_nano.onnx.

Esse arquivo foi testado manualmente contra imagens reais durante o
desenvolvimento deste projeto: input esperado [1, 3, 416, 416] e
output raw [1, 3549, 85] (formato padrao do YOLOX antes do decode).

Uso:
    python scripts/download_model.py
"""

from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/"
    "0.1.1rc0/yolox_nano.onnx"
)
DEST = Path(__file__).resolve().parent.parent / "models" / "yolox_nano.onnx"

# yolox_nano.onnx fica em torno de 3.5 MB; qualquer coisa bem menor que isso
# geralmente e uma pagina de erro (404/redirect) salva no lugar do binario.
MIN_EXPECTED_SIZE = 1_000_000


def _is_valid_onnx(path: Path) -> bool:
    if path.stat().st_size < MIN_EXPECTED_SIZE:
        return False
    with path.open("rb") as f:
        header = f.read(4)
    # arquivo ONNX comeca com bytes de protobuf, nao com "<" (HTML) ou "{" (JSON)
    return header[:1] not in (b"<", b"{")


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)

    if DEST.exists():
        if _is_valid_onnx(DEST):
            print(f"Modelo ja existe em {DEST}, nada a fazer.")
            return
        print(f"Modelo existente em {DEST} parece corrompido/incompleto, baixando de novo.")
        DEST.unlink()

    print(f"Baixando {MODEL_URL}")
    try:
        urllib.request.urlretrieve(MODEL_URL, DEST)
    except Exception as exc:
        DEST.unlink(missing_ok=True)
        print(f"Falha ao baixar o modelo: {exc}", file=sys.stderr)
        sys.exit(1)

    if not _is_valid_onnx(DEST):
        size = DEST.stat().st_size
        DEST.unlink(missing_ok=True)
        print(
            f"Download retornou arquivo invalido ({size} bytes) em vez do modelo ONNX.",
            file=sys.stderr,
        )
        sys.exit(1)

    size_mb = DEST.stat().st_size / (1024 * 1024)
    print(f"Modelo salvo em {DEST} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
