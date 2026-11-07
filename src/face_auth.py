"""
FaceAuth

Reconhece "pessoas confiaveis" pelo rosto, para o X9 nao bloquear o PC
quando quem sentou foi o proprio dono.

Usa dois modelos do opencv_zoo que rodam pelo proprio OpenCV, 100%
local:
  * YuNet: acha os rostos no frame;
  * SFace: transforma cada rosto num vetor de 128 numeros. Dois rostos
    da mesma pessoa dao vetores parecidos (similaridade de cosseno alta).

O que fica salvo em disco e so esse vetor (trusted_faces.npy), nunca a
foto. Mesmo assim e dado biometrico: fica na pasta do usuario e nao sai
da maquina.

Regra de decisao, pensada para errar para o lado seguro:
  * todos os rostos no frame batem com alguem cadastrado -> "trusted";
  * qualquer rosto que nao bate -> "unknown";
  * nenhum rosto visivel (de costas, escuro) -> "no_face", que o X9
    trata igual a desconhecido.

Limite conhecido: nao ha deteccao de pessoa viva. Uma foto impressa ou
na tela do celular do dono pode enganar. Por isso o X9 continua
avisando mesmo quando reconhece alguem confiavel.

Nao sabe nada sobre camera, notificacao ou bloqueio.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List, Literal

import cv2
import numpy as np

logger = logging.getLogger("x9.face_auth")

Verdict = Literal["trusted", "unknown", "no_face"]


def decide(
    faces: np.ndarray, trusted: np.ndarray, threshold: float
) -> tuple[Verdict, float]:
    """Compara rostos (N x 128, normalizados) com os cadastrados.

    Retorna o veredito e a pior similaridade encontrada (o rosto menos
    parecido com qualquer cadastrado), util para log e ajuste.
    """
    if len(faces) == 0:
        return "no_face", 0.0
    if len(trusted) == 0:
        return "unknown", 0.0
    best_per_face = (faces @ trusted.T).max(axis=1)
    worst = float(best_per_face.min())
    return ("trusted" if worst >= threshold else "unknown"), worst


class FaceAuth:
    def __init__(
        self,
        detector_model: Path,
        recognizer_model: Path,
        store_path: Path,
        threshold: float = 0.45,
        min_face_score: float = 0.8,
    ) -> None:
        self._detector = cv2.FaceDetectorYN.create(
            str(detector_model), "", (320, 320), min_face_score
        )
        self._recognizer = cv2.FaceRecognizerSF.create(str(recognizer_model), "")
        self._store_path = Path(store_path)
        self._threshold = threshold
        self._trusted = self._load()

    # ---------- cadastro ----------

    @property
    def trusted_count(self) -> int:
        return len(self._trusted)

    def enroll(self, frames: Iterable[np.ndarray]) -> int:
        """Cadastra o rosto a partir de frames com exatamente um rosto.

        Frames com zero ou mais de um rosto sao ignorados, para nao
        cadastrar sem querer outra pessoa que apareceu ao fundo.
        Retorna quantas amostras foram adicionadas.
        """
        new = []
        for frame in frames:
            embeddings = self.embeddings(frame)
            if len(embeddings) == 1:
                new.append(embeddings[0])
        return self.add_embeddings(new)

    def add_embeddings(self, embeddings: List[np.ndarray]) -> int:
        """Grava vetores ja calculados (ex.: vindos do cadastro guiado)."""
        if not embeddings:
            return 0
        self._trusted = np.vstack(
            [self._trusted, np.array(embeddings, dtype=np.float32).reshape(-1, 128)]
        )
        self._save()
        logger.info("%d amostra(s) de rosto cadastrada(s)", len(embeddings))
        return len(embeddings)

    def clear(self) -> None:
        self._trusted = np.zeros((0, 128), dtype=np.float32)
        self._store_path.unlink(missing_ok=True)
        logger.info("Rostos confiaveis apagados")

    # ---------- reconhecimento ----------

    def detect(self, frame: np.ndarray) -> np.ndarray:
        """Rostos do frame no formato do YuNet (N x 15: caixa, 5 pontos, nota)."""
        h, w = frame.shape[:2]
        self._detector.setInputSize((w, h))
        _, faces = self._detector.detect(frame)
        return np.zeros((0, 15), dtype=np.float32) if faces is None else faces

    def embed(self, frame: np.ndarray, face: np.ndarray) -> np.ndarray:
        """Vetor normalizado (128) de um rosto ja detectado."""
        aligned = self._recognizer.alignCrop(frame, face)
        vec = self._recognizer.feature(aligned).flatten().astype(np.float32)
        norm = np.linalg.norm(vec)
        return vec / norm if norm > 0 else vec

    def embeddings(self, frame: np.ndarray) -> np.ndarray:
        """Vetores normalizados (N x 128) de todos os rostos do frame."""
        out = [self.embed(frame, face) for face in self.detect(frame)]
        return np.array(out, dtype=np.float32).reshape(-1, 128)

    def classify(self, frame: np.ndarray) -> Verdict:
        verdict, score = decide(self.embeddings(frame), self._trusted, self._threshold)
        logger.info("Rosto: %s (similaridade %.2f, limite %.2f)", verdict, score, self._threshold)
        return verdict

    # ---------- disco ----------

    def _load(self) -> np.ndarray:
        if self._store_path.exists():
            try:
                data = np.load(self._store_path).astype(np.float32)
                if data.ndim == 2 and data.shape[1] == 128:
                    return data
                logger.warning("trusted_faces.npy em formato inesperado, ignorado")
            except (OSError, ValueError):
                logger.exception("Falha ao ler %s", self._store_path)
        return np.zeros((0, 128), dtype=np.float32)

    def _save(self) -> None:
        self._store_path.parent.mkdir(parents=True, exist_ok=True)
        np.save(self._store_path, self._trusted)
