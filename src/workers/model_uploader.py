'''Background worker for loading a YOLO model.'''

import logging

from PySide6.QtCore import QObject, Signal, Slot

from src.device import resolve_device

logger = logging.getLogger(__name__)


class ModelUploadWorker(QObject):
    modelLoaded = Signal(object, str)
    error = Signal(str)

    def __init__(self, model_path, confidence_threshold=0.5,
                 device_preference='auto'):
        super().__init__()
        self.model_path = model_path
        self.confidence_threshold = confidence_threshold
        self.device_preference = device_preference

    @Slot()
    def load_model(self):
        try:
            from sahi.auto_model import AutoDetectionModel

            device = resolve_device(self.device_preference)
            model = AutoDetectionModel.from_pretrained(
                model_type='yolov8',
                model_path=self.model_path,
                confidence_threshold=self.confidence_threshold,
                device=device,
            )
            self.modelLoaded.emit(model, device)
        except Exception as exc:
            logger.exception('Model loading failed')
            self.error.emit(str(exc))
