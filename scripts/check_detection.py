"""
Utilitario para validar a instalacao antes de confiar na webcam.

Roda o PersonDetector contra uma imagem estatica e mostra se
encontrou uma pessoa e com qual confianca. Util para confirmar que
o modelo, o ONNX Runtime e as dependencias estao instalados
corretamente antes de rodar o agente de verdade.

Uso:
    python scripts/check_detection.py caminho/para/imagem.jpg
"""

from __future__ import annotations

import sys
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from detector import PersonDetector  # noqa: E402


def main() -> None:
    if len(sys.argv) != 2:
        print("Uso: python scripts/check_detection.py caminho/para/imagem.jpg")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"Imagem nao encontrada: {image_path}")
        sys.exit(1)

    frame = cv2.imread(str(image_path))
    if frame is None:
        print(f"Nao foi possivel ler a imagem: {image_path}")
        sys.exit(1)

    project_root = Path(__file__).resolve().parent.parent
    model_path = project_root / "models" / "yolox_nano.onnx"

    detector = PersonDetector(model_path=str(model_path), confidence=0.60)
    detected, confidence = detector.detect_person(frame)

    if detected:
        print(f"Pessoa detectada, confianca {confidence:.2f}")
    else:
        print("Nenhuma pessoa detectada nessa imagem")


if __name__ == "__main__":
    main()
