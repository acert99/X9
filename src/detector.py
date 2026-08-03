"""
PersonDetector

Roda o modelo YOLOX Nano (ONNX) sobre um frame e informa se existe
ao menos uma pessoa detectada acima do limiar de confianca configurado.

O pre e pos processamento seguem o formato oficial do YOLOX
(letterbox resize + decode de grade com strides 8, 16 e 32),
ja que os modelos exportados pelo projeto original nao incluem
o decode dentro do proprio grafo ONNX.

Este modulo nao sabe nada sobre camera, notificacao ou janelas
temporais de confirmacao. Ele responde uma pergunta simples para
cada frame: "tem pessoa aqui, sim ou nao, com qual confianca".
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple

import cv2
import numpy as np
import onnxruntime as ort

logger = logging.getLogger("x9.detector")

COCO_PERSON_CLASS_ID = 0
YOLOX_STRIDES = (8, 16, 32)


@dataclass
class Detection:
    confidence: float
    box_xyxy: Tuple[float, float, float, float]


class PersonDetector:
    def __init__(
        self,
        model_path: str,
        input_size: int = 416,
        confidence: float = 0.60,
        nms_threshold: float = 0.45,
    ) -> None:
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(
                f"Modelo nao encontrado em {model_file.resolve()}. "
                "Rode scripts/download_model.py antes de iniciar o agente."
            )

        self._input_size = (input_size, input_size)
        self._confidence = confidence
        self._nms_threshold = nms_threshold

        self._session = ort.InferenceSession(
            str(model_file), providers=["CPUExecutionProvider"]
        )
        self._input_name = self._session.get_inputs()[0].name
        logger.info("Modelo carregado de %s", model_file)

    def detect_person(self, frame: np.ndarray) -> Tuple[bool, float]:
        """Roda o detector sobre um frame.

        Retorna (pessoa_detectada, confianca_maxima).
        """
        detections = self._infer(frame)
        if not detections:
            return False, 0.0
        best = max(detections, key=lambda d: d.confidence)
        return True, best.confidence

    def _infer(self, frame: np.ndarray) -> List[Detection]:
        padded, ratio = self._preprocess(frame)
        raw_output = self._session.run(None, {self._input_name: padded[None, ...]})[0]
        decoded = self._decode_outputs(raw_output)[0]
        return self._postprocess(decoded, ratio)

    def _preprocess(self, img: np.ndarray) -> Tuple[np.ndarray, float]:
        h, w = self._input_size
        padded_img = np.full((h, w, 3), 114, dtype=np.uint8)

        r = min(h / img.shape[0], w / img.shape[1])
        resized = cv2.resize(
            img,
            (int(img.shape[1] * r), int(img.shape[0] * r)),
            interpolation=cv2.INTER_LINEAR,
        ).astype(np.uint8)
        padded_img[: resized.shape[0], : resized.shape[1]] = resized

        padded_img = padded_img.transpose((2, 0, 1))
        padded_img = np.ascontiguousarray(padded_img, dtype=np.float32)
        return padded_img, r

    def _decode_outputs(self, outputs: np.ndarray) -> np.ndarray:
        grids = []
        expanded_strides = []
        h, w = self._input_size

        for stride in YOLOX_STRIDES:
            hsize, wsize = h // stride, w // stride
            xv, yv = np.meshgrid(np.arange(wsize), np.arange(hsize))
            grid = np.stack((xv, yv), 2).reshape(1, -1, 2)
            grids.append(grid)
            expanded_strides.append(np.full((*grid.shape[:2], 1), stride))

        grids = np.concatenate(grids, 1)
        expanded_strides = np.concatenate(expanded_strides, 1)

        outputs[..., :2] = (outputs[..., :2] + grids) * expanded_strides
        outputs[..., 2:4] = np.exp(outputs[..., 2:4]) * expanded_strides
        return outputs

    def _postprocess(self, decoded: np.ndarray, ratio: float) -> List[Detection]:
        boxes = decoded[:, :4]
        obj_conf = decoded[:, 4:5]
        cls_conf = decoded[:, 5:]
        scores = obj_conf * cls_conf

        person_scores = scores[:, COCO_PERSON_CLASS_ID]
        mask = person_scores > self._confidence
        if not np.any(mask):
            return []

        boxes_xyxy = np.empty_like(boxes[mask])
        selected = boxes[mask]
        boxes_xyxy[:, 0] = selected[:, 0] - selected[:, 2] / 2.0
        boxes_xyxy[:, 1] = selected[:, 1] - selected[:, 3] / 2.0
        boxes_xyxy[:, 2] = selected[:, 0] + selected[:, 2] / 2.0
        boxes_xyxy[:, 3] = selected[:, 1] + selected[:, 3] / 2.0
        boxes_xyxy /= ratio

        selected_scores = person_scores[mask]
        keep = self._nms(boxes_xyxy, selected_scores)

        return [
            Detection(confidence=float(selected_scores[i]), box_xyxy=tuple(boxes_xyxy[i]))
            for i in keep
        ]

    def _nms(self, boxes: np.ndarray, scores: np.ndarray) -> List[int]:
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1) * (y2 - y1)
        order = scores.argsort()[::-1]
        keep: List[int] = []

        while order.size > 0:
            i = order[0]
            keep.append(int(i))
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            w = np.maximum(0.0, xx2 - xx1)
            h = np.maximum(0.0, yy2 - yy1)
            inter = w * h
            iou = inter / (areas[i] + areas[order[1:]] - inter)
            order = order[1:][iou <= self._nms_threshold]

        return keep
