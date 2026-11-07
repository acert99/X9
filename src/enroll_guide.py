"""
Roteiro do cadastro guiado de rosto.

Cadastrar so de frente faz o X9 reconhecer o dono so de frente. Este
roteiro pede poses variadas (virar para os lados, queixo para cima e
para baixo, perto e longe) e so aceita a amostra quando a pose foi
realmente feita, medida pelos pontos do rosto que o YuNet devolve
(olhos, nariz e cantos da boca).

As poses sao medidas em relacao a primeira etapa (de frente), e os
lados sao comparados entre si em vez de "esquerda/direita" fixos:
assim tanto faz se a camera espelha a imagem ou nao (iVCam, por
exemplo, pode espelhar).

Nao sabe nada de camera, janela ou modelo: recebe medidas e diz se
aceitou. Por isso da para testar sem webcam.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np


@dataclass(frozen=True)
class Pose:
    yaw: float    # >0 nariz para um lado, <0 para o outro (0 = de frente)
    pitch: float  # posicao do nariz entre olhos (0) e boca (1)
    size: float   # largura do rosto / largura do frame


def pose_from_face(face: np.ndarray, frame_width: int) -> Pose:
    """Mede a pose a partir de uma linha do YuNet:
    [x, y, w, h, olho_d(x,y), olho_e(x,y), nariz(x,y), boca_d(x,y), boca_e(x,y), score]
    """
    x, y, w, h = face[0:4]
    re, le, nose = face[4:6], face[6:8], face[8:10]
    rm, lm = face[10:12], face[12:14]
    eyes_mid = (re + le) / 2
    eye_dist = max(abs(le[0] - re[0]), 1e-6)
    mouth_y = (rm[1] + lm[1]) / 2
    eye_to_mouth = max(mouth_y - eyes_mid[1], 1e-6)
    return Pose(
        yaw=float((nose[0] - eyes_mid[0]) / eye_dist),
        pitch=float((nose[1] - eyes_mid[1]) / eye_to_mouth),
        size=float(w / max(frame_width, 1)),
    )


YAW_FRONT = 0.18      # de frente (folga para camera ao lado do monitor)
YAW_TURN = 0.15       # virou: ~20 graus ou mais
PITCH_TILT = 0.07     # levantou/abaixou o queixo
SIZE_NEAR = 1.25      # 25% maior que na etapa de frente
SIZE_FAR = 0.80       # 20% menor


@dataclass
class Step:
    key: str
    instruction: str


STEPS: List[Step] = [
    Step("front", "Olhe direto para a camera"),
    Step("side1", "Vire o rosto devagar para um lado"),
    Step("side2", "Agora vire para o OUTRO lado"),
    Step("tilt1", "Levante um pouco o queixo"),
    Step("tilt2", "Agora abaixe um pouco o queixo"),
    Step("near", "Chegue mais perto da camera"),
    Step("far", "Afaste-se um pouco"),
]


@dataclass
class GuidedEnrollment:
    samples_per_step: int = 3
    step_index: int = 0
    accepted: List[np.ndarray] = field(default_factory=list)
    _count_in_step: int = 0
    _base: Optional[Pose] = None
    _side_sign: float = 0.0
    _tilt_sign: float = 0.0
    _front_poses: List[Pose] = field(default_factory=list)

    @property
    def done(self) -> bool:
        return self.step_index >= len(STEPS)

    @property
    def current(self) -> Optional[Step]:
        return None if self.done else STEPS[self.step_index]

    @property
    def progress(self) -> tuple[int, int]:
        """(amostras desta etapa, amostras necessarias)."""
        return self._count_in_step, self.samples_per_step

    def matches(self, pose: Pose) -> bool:
        """A pose atual cumpre o que a etapa pede?"""
        step = self.current
        if step is None:
            return False
        if step.key == "front":
            return abs(pose.yaw) < YAW_FRONT
        base = self._base
        dyaw = pose.yaw - base.yaw
        dpitch = pose.pitch - base.pitch
        if step.key == "side1":
            return abs(dyaw) > YAW_TURN
        if step.key == "side2":
            return dyaw * self._side_sign < -YAW_TURN
        if step.key == "tilt1":
            return abs(dpitch) > PITCH_TILT and abs(dyaw) < YAW_TURN
        if step.key == "tilt2":
            return dpitch * self._tilt_sign < -PITCH_TILT and abs(dyaw) < YAW_TURN
        if step.key == "near":
            return pose.size > base.size * SIZE_NEAR
        if step.key == "far":
            return pose.size < base.size * SIZE_FAR
        return False

    def feed(self, pose: Pose, embedding: np.ndarray) -> bool:
        """Oferece uma amostra. Retorna True se foi aceita."""
        if not self.matches(pose):
            return False
        step = self.current
        if step.key == "front":
            self._front_poses.append(pose)
        elif step.key == "side1" and self._side_sign == 0.0:
            self._side_sign = float(np.sign(pose.yaw - self._base.yaw))
        elif step.key == "tilt1" and self._tilt_sign == 0.0:
            self._tilt_sign = float(np.sign(pose.pitch - self._base.pitch))
        self.accepted.append(embedding)
        self._count_in_step += 1
        if self._count_in_step >= self.samples_per_step:
            self._advance()
        return True

    def skip(self) -> None:
        """Pula a etapa atual (ex.: tempo esgotado). De frente nao pula:
        sem ela nao ha referencia para medir as outras poses."""
        if self.current is not None and self.current.key != "front":
            self._advance()

    def _advance(self) -> None:
        if self.current is not None and self.current.key == "front":
            self._base = Pose(
                yaw=float(np.mean([p.yaw for p in self._front_poses])),
                pitch=float(np.mean([p.pitch for p in self._front_poses])),
                size=float(np.mean([p.size for p in self._front_poses])),
            )
        self.step_index += 1
        self._count_in_step = 0
