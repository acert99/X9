"""
Baixa os modelos ONNX usados pelo X9 e salva em models/.

* yolox_nano.onnx: detector de pessoas (YOLOX, Megvii, Apache 2.0).
  Testado contra imagens reais: input [1, 3, 416, 416], output raw
  [1, 3549, 85] (formato padrao do YOLOX antes do decode).
* face_detection_yunet_2023mar.onnx: detector de rostos (YuNet,
  opencv_zoo, MIT). Usado so no reconhecimento de pessoa confiavel.
* face_recognition_sface_2021dec.onnx: reconhecedor de rostos (SFace,
  opencv_zoo, Apache 2.0). Usado so no reconhecimento de pessoa
  confiavel.

Uso:
    python scripts/download_model.py
"""

from __future__ import annotations

import hashlib
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path

MODELS_DIR = Path(__file__).resolve().parent.parent / "models"
_ZOO = "https://github.com/opencv/opencv_zoo/raw/main/models"


@dataclass(frozen=True)
class Model:
    filename: str
    url: str
    sha256: str
    size: int


# Hashes dos arquivos oficiais. Os modelos sao carregados e executados
# pelo ONNX Runtime / OpenCV, entao um arquivo trocado no meio do
# caminho seria codigo de terceiro rodando na maquina de quem instalou.
# Se o hash nao bater, o download e descartado em vez de usado.
MODELS = [
    Model(
        "yolox_nano.onnx",
        "https://github.com/Megvii-BaseDetection/YOLOX/releases/download/"
        "0.1.1rc0/yolox_nano.onnx",
        "c789161ed43c8269fcd4e67c67eeeb4e80c622da2eb296a20bc6007bd18a0b7d",
        3_659_407,
    ),
    Model(
        "face_detection_yunet_2023mar.onnx",
        f"{_ZOO}/face_detection_yunet/face_detection_yunet_2023mar.onnx",
        "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4",
        232_589,
    ),
    Model(
        "face_recognition_sface_2021dec.onnx",
        f"{_ZOO}/face_recognition_sface/face_recognition_sface_2021dec.onnx",
        "0ba9fbfa01b5270c96627c4ef784da859931e02f04419c829e83484087c34e79",
        38_696_353,
    ),
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_valid(path: Path, model: Model) -> bool:
    """Confere se o arquivo em disco e exatamente o modelo esperado."""
    return path.stat().st_size == model.size and _sha256(path) == model.sha256


def fetch(model: Model) -> bool:
    dest = MODELS_DIR / model.filename

    if dest.exists():
        if _is_valid(dest, model):
            print(f"{model.filename}: ja existe e o hash confere.")
            return True
        print(f"{model.filename}: arquivo existente nao confere, baixando de novo.")
        dest.unlink()

    if not model.url.startswith("https://"):
        print(f"{model.filename}: URL precisa usar https.", file=sys.stderr)
        return False

    print(f"Baixando {model.url}")
    try:
        urllib.request.urlretrieve(model.url, dest)
    except Exception as exc:
        dest.unlink(missing_ok=True)
        print(f"{model.filename}: falha ao baixar: {exc}", file=sys.stderr)
        return False

    if not _is_valid(dest, model):
        size = dest.stat().st_size
        actual = _sha256(dest)
        dest.unlink(missing_ok=True)
        print(
            f"{model.filename}: o arquivo baixado nao confere com o oficial e\n"
            "foi descartado. Nada foi instalado.\n"
            f"  tamanho esperado: {model.size} bytes / recebido: {size} bytes\n"
            f"  sha256 esperado:  {model.sha256}\n"
            f"  sha256 recebido:  {actual}",
            file=sys.stderr,
        )
        return False

    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"{model.filename}: salvo ({size_mb:.1f} MB), sha256 conferido.")
    return True


def main() -> None:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    ok = all([fetch(m) for m in MODELS])
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
