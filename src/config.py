"""
ConfigManager

Responsavel por carregar e validar o arquivo config.yaml.
Nao conhece nada sobre camera, detector ou notificacao alem dos
valores de configuracao. Qualquer outro modulo que precise de
configuracao recebe um objeto Config ja validado.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Dict, List, Type, TypeVar

import yaml

T = TypeVar("T")


def _known_fields(cls: Type[T], raw: Dict[str, Any]) -> Dict[str, Any]:
    """Descarta chaves desconhecidas (ex.: config.yaml antigo com campo removido)."""
    valid = {f.name for f in fields(cls)}
    return {k: v for k, v in raw.items() if k in valid}


@dataclass
class CameraConfig:
    index: int = 0
    width: int = 640
    height: int = 480
    fps: int = 3
    open_retries: int = 3
    open_retry_delay_seconds: float = 2.0


@dataclass
class DetectorConfig:
    input_size: int = 416
    confidence: float = 0.60
    nms_threshold: float = 0.45
    positive_frames: int = 5
    window_seconds: float = 3.0


@dataclass
class NotificationConfig:
    cooldown_seconds: int = 600
    urls: List[str] = field(default_factory=list)
    title: str = "Presence Agent"
    message: str = "Presenca detectada no computador"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "presence_agent.log"


@dataclass
class Config:
    camera: CameraConfig = field(default_factory=CameraConfig)
    detector: DetectorConfig = field(default_factory=DetectorConfig)
    notification: NotificationConfig = field(default_factory=NotificationConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, path: str | Path = "config.yaml") -> "Config":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"Arquivo de configuracao nao encontrado em {path.resolve()}. "
                "Copie config.yaml.example para config.yaml e ajuste os valores."
            )

        with open(path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

        camera = CameraConfig(**_known_fields(CameraConfig, raw.get("camera", {})))
        detector = DetectorConfig(**_known_fields(DetectorConfig, raw.get("detector", {})))
        notification = NotificationConfig(
            **_known_fields(NotificationConfig, raw.get("notification", {}))
        )
        logging_cfg = LoggingConfig(**_known_fields(LoggingConfig, raw.get("logging", {})))

        config = cls(
            camera=camera,
            detector=detector,
            notification=notification,
            logging=logging_cfg,
        )
        config._validate()
        return config

    def _validate(self) -> None:
        if not self.notification.urls:
            raise ValueError(
                "Nenhuma URL de notificacao configurada em notification.urls. "
                "Adicione ao menos uma URL no formato aceito pelo Apprise, "
                "por exemplo ntfy://ntfy.sh/SEU_TOPICO."
            )
        if self.detector.positive_frames < 1:
            raise ValueError("detector.positive_frames deve ser maior ou igual a 1")
        if self.camera.fps <= 0:
            raise ValueError("camera.fps deve ser maior que zero")
