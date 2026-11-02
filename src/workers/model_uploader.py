'''Background worker for loading a YOLO model.'''

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from src.device import resolve_device

logger = logging.getLogger(__name__)

SUPPORTED_MODEL_FORMATS = {'.pt', '.onnx', '.engine'}


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

            suffix = Path(self.model_path).suffix.lower()
            if suffix not in SUPPORTED_MODEL_FORMATS:
                raise ValueError('Choose a YOLO .pt, .onnx, or .engine model.')
            device = resolve_device(self.device_preference)
            if suffix == '.engine' and not device.startswith('cuda'):
                raise ValueError('TensorRT .engine models require an NVIDIA GPU.')
            if suffix == '.onnx' and device.startswith('cuda'):
                import onnxruntime

                if 'CUDAExecutionProvider' not in onnxruntime.get_available_providers():
                    logger.warning(
                        'ONNX Runtime CUDA provider is unavailable; using CPU inference.'
                    )
                    device = 'cpu'
            model = AutoDetectionModel.from_pretrained(
                model_type='yolov8',
                model_path=self.model_path,
                confidence_threshold=self.confidence_threshold,
                device=device,
            )
            if suffix == '.engine':
                logger.info('Loading and warming up TensorRT engine')
                model.warmup()
            self.modelLoaded.emit(model, device)
        except Exception as exc:
            logger.exception('Model loading failed')
            self.error.emit(str(exc))
