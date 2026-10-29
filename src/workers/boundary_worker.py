'''Worker wrapper for the optional interactive boundary tool.'''

import logging

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger(__name__)


class BoundaryWorker(QObject):
    boundaryGenerated = Signal(list)
    error = Signal(str)

    def __init__(self, tif_path, scale=10):
        super().__init__()
        self.tif_path = tif_path
        self.scale = scale

    @Slot()
    def generate_boundary(self):
        try:
            from ..boundary.generate_boundary import plot_and_capture_points

            points = plot_and_capture_points(self.tif_path, self.scale)
            self.boundaryGenerated.emit(points)
        except Exception as exc:
            logger.exception('Boundary generation failed')
            self.error.emit(str(exc))
