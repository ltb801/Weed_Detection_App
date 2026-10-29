'''Background worker for memory-bounded GeoTIFF detection.'''

import logging
import threading
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

from src.summary import DetectionSummary, summarize_detections

logger = logging.getLogger(__name__)


class DetectionCancelled(Exception):
    '''Raised internally when the user cancels sliced inference.'''


@dataclass
class DetectionResult:
    image_path: str
    image_width: int
    image_height: int
    object_prediction_list: list
    summary: DetectionSummary | None = None
    transform: object | None = None
    crs: object | None = None

    def to_coco_annotations(self):
        return [prediction.to_coco_prediction().json for prediction in self.object_prediction_list]


def detect_geotiff(image_path, detection_model, slice_height, slice_width,
                   overlap_height_ratio, overlap_width_ratio, progress_callback):
    '''Read and infer one raster window at a time, never decoding the whole TIFF.'''
    import rasterio
    from rasterio.windows import Window
    from sahi.postprocess.combine import GreedyNMMPostprocess
    from sahi.predict import get_prediction
    from sahi.slicing import get_slice_bboxes

    from .image_worker import _to_uint8

    with rasterio.open(image_path) as source:
        if source.count < 3:
            raise ValueError('Detection requires a GeoTIFF with at least three colour bands.')
        bboxes = get_slice_bboxes(
            image_height=source.height,
            image_width=source.width,
            slice_height=slice_height,
            slice_width=slice_width,
            overlap_height_ratio=overlap_height_ratio,
            overlap_width_ratio=overlap_width_ratio,
        )
        postprocess = GreedyNMMPostprocess(match_threshold=0.5, match_metric='IOS')
        predictions = []
        total = len(bboxes)
        for index, (left, top, right, bottom) in enumerate(bboxes, start=1):
            progress_callback(index, total)
            window = Window(left, top, right - left, bottom - top)
            tile = source.read([1, 2, 3], window=window)
            tile = _to_uint8(tile.transpose(1, 2, 0))
            result = get_prediction(
                image=tile,
                detection_model=detection_model,
                shift_amount=[left, top],
                full_shape=[source.height, source.width],
            )
            predictions.extend(
                prediction.get_shifted_object_prediction()
                for prediction in result.object_prediction_list
            )
            if len(predictions) > 1000:
                predictions = postprocess(predictions)

        if len(predictions) > 1:
            predictions = postprocess(predictions)
        summary = summarize_detections(
            predictions, source.width, source.height, source.transform, source.crs,
        )
        return DetectionResult(
            str(image_path), source.width, source.height, predictions,
            summary, source.transform, source.crs,
        )


class DetectWorker(QObject):
    '''Run windowed inference without blocking the Qt GUI thread.'''

    progress = Signal(int, int)
    statusChanged = Signal(str)
    finished = Signal(object)
    cancelled = Signal()
    error = Signal(str)

    def __init__(self, image_path, detection_model, slice_height, slice_width,
                 overlap_height_ratio, overlap_width_ratio):
        super().__init__()
        self.image_path = image_path
        self.detection_model = detection_model
        self.slice_height = slice_height
        self.slice_width = slice_width
        self.overlap_height_ratio = overlap_height_ratio
        self.overlap_width_ratio = overlap_width_ratio
        self._cancel_requested = threading.Event()

    def request_cancel(self):
        self._cancel_requested.set()

    @Slot()
    def run(self):
        try:
            self.statusChanged.emit('Preparing image slices...')

            def report_progress(current_slice, total_slices):
                if self._cancel_requested.is_set():
                    raise DetectionCancelled
                self.progress.emit(current_slice, total_slices)
                self.statusChanged.emit(f'Detecting slice {current_slice} of {total_slices}...')

            if Path(self.image_path).suffix.lower() not in {'.tif', '.tiff'}:
                raise ValueError('Detection requires a GeoTIFF image.')
            result = detect_geotiff(
                self.image_path, self.detection_model, self.slice_height,
                self.slice_width, self.overlap_height_ratio,
                self.overlap_width_ratio, report_progress,
            )
            if self._cancel_requested.is_set():
                raise DetectionCancelled
            self.finished.emit(result)
        except DetectionCancelled:
            self.cancelled.emit()
        except Exception as exc:
            logger.exception('Detection failed')
            self.error.emit(str(exc))
