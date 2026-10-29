'''Background worker for exporting a detection visualization.'''

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)


def export_visual(result, output_path, max_width=4096):
    '''Render a bounded-size preview while keeping JSON coordinates at source resolution.'''
    import cv2
    import numpy as np
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling

    from .image_worker import _to_uint8

    with rasterio.open(result.image_path) as source:
        width = min(source.width, max_width)
        height = max(1, round(source.height * width / source.width))
        data = source.read(
            [1, 2, 3], out_shape=(3, height, width),
            resampling=Resampling.bilinear,
        ).transpose(1, 2, 0)
        image = _to_uint8(data)
        scale_x = width / source.width
        scale_y = height / source.height

    for prediction in result.object_prediction_list:
        if prediction.mask:
            for polygon in prediction.mask.segmentation:
                points = np.asarray(polygon, dtype=np.float32).reshape(-1, 2)
                if len(points) >= 3:
                    points[:, 0] *= scale_x
                    points[:, 1] *= scale_y
                    cv2.polylines(image, [points.astype(np.int32)], True, (255, 255, 0), 2)
        else:
            x1, y1, x2, y2 = prediction.bbox.to_xyxy()
            cv2.rectangle(
                image,
                (round(x1 * scale_x), round(y1 * scale_y)),
                (round(x2 * scale_x), round(y2 * scale_y)),
                (255, 255, 0), 2,
            )
    Image.fromarray(image).save(output_path)


class ExportWorker(QObject):
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, prediction_result, export_directory):
        super().__init__()
        self.prediction_result = prediction_result
        self.export_directory = export_directory

    @Slot()
    def export(self):
        try:
            from sahi.utils.file import save_json

            Path(self.export_directory).mkdir(parents=True, exist_ok=True)
            output_path = Path(self.export_directory) / 'prediction_visual.png'
            export_visual(self.prediction_result, output_path)
            save_json(
                self.prediction_result.to_coco_annotations(),
                Path(self.export_directory) / 'detections.json',
                indent=2,
            )
            self.finished.emit(str(output_path))
        except Exception as exc:
            logger.exception('Result export failed')
            self.error.emit(str(exc))
