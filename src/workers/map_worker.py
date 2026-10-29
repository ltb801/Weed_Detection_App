'''Scaffold for the optional prescription-map feature.'''

from PySide6.QtCore import QObject, Signal, Slot


class PrescriptionMapWorker(QObject):
    mapCreated = Signal(object)
    error = Signal(str)

    def __init__(self, coco_results, geotiff_path, output_path, spraying_rate):
        super().__init__()
        self.coco_results = coco_results
        self.geotiff_path = geotiff_path
        self.output_path = output_path
        self.spraying_rate = spraying_rate

    @Slot()
    def create_prescription_map(self):
        self.error.emit(
            'Prescription-map generation is not implemented yet. '
            'The previous placeholder called itself recursively and has been disabled.'
        )
