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

import hashlib
import sys
import urllib.request
from pathlib import Path

MODEL_URL = (
    "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/"
    "0.1.1rc0/yolox_nano.onnx"
)
DEST = Path(__file__).resolve().parent.parent / "models" / "yolox_nano.onnx"

# Hash do arquivo oficial publicado no release acima, conferido em
# downloads independentes. O modelo e carregado e executado pelo ONNX
# Runtime, entao um arquivo trocado no meio do caminho seria codigo
# de terceiro rodando na maquina de quem instalou. Se o hash nao bater,
# o download e descartado em vez de usado.
EXPECTED_SHA256 = "c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d"
EXPECTED_SIZE = 3_659_407


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_valid_onnx(path: Path) -> bool:
    """Confere se o arquivo em disco e exatamente o modelo esperado."""
    return path.stat().st_size == EXPECTED_SIZE and _sha256(path) == EXPECTED_SHA256


def main() -> None:
    DEST.parent.mkdir(parents=True, exist_ok=True)

    if DEST.exists():
        if _is_valid_onnx(DEST):
            print(f"Modelo ja existe em {DEST} e o hash confere, nada a fazer.")
            return
        print(
            f"Modelo existente em {DEST} nao confere com o esperado "
            "(corrompido, incompleto ou alterado), baixando de novo."
        )
        DEST.unlink()

    if not MODEL_URL.startswith("https://"):
        print("MODEL_URL precisa usar https.", file=sys.stderr)
        sys.exit(1)

    print(f"Baixando {MODEL_URL}")
    try:
        urllib.request.urlretrieve(MODEL_URL, DEST)
    except Exception as exc:
        DEST.unlink(missing_ok=True)
        print(f"Falha ao baixar o modelo: {exc}", file=sys.stderr)
        sys.exit(1)

    if not _is_valid_onnx(DEST):
        size = DEST.stat().st_size
        actual = _sha256(DEST)
        DEST.unlink(missing_ok=True)
        print(
            "O arquivo baixado nao confere com o modelo oficial esperado e foi\n"
            "descartado. Nada foi instalado.\n"
            f"  tamanho esperado: {EXPECTED_SIZE} bytes / recebido: {size} bytes\n"
            f"  sha256 esperado:  {EXPECTED_SHA256}\n"
            f"  sha256 recebido:  {actual}",
            file=sys.stderr,
        )
        sys.exit(1)

    size_mb = DEST.stat().st_size / (1024 * 1024)
    print(f"Modelo salvo em {DEST} ({size_mb:.1f} MB), sha256 conferido.")


if __name__ == "__main__":
    main()
