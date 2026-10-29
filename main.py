'''Entry point and controller for the Weed Detection App.'''

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QSettings, QThread
from PySide6.QtGui import QCloseEvent, QPixmap
from PySide6.QtWidgets import QApplication, QFileDialog, QMainWindow, QMessageBox

from src.config import PREVIEW_DOWNSAMPLE_FACTOR
from src.device import resolve_device
from src.ui.main_window import UI_MainWindow
from src.ui.theme import apply_app_theme

PROJECT_ROOT = Path(__file__).resolve().parent
logger = logging.getLogger(__name__)


def configure_logging():
    log_directory = PROJECT_ROOT / 'logs'
    log_directory.mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s: %(message)s',
        handlers=[
            logging.FileHandler(log_directory / 'weed_detection.log', encoding='utf-8'),
            logging.StreamHandler(),
        ],
    )


class WeedDetectionApp(QMainWindow, UI_MainWindow):
    def __init__(self):
        super().__init__()
        self.initUI(self)
        self.imageView.detectionClicked.connect(self._on_detection_clicked)

        self.settings = QSettings('WeedDetectionApp', 'WeedDetectionApp')
        self.detection_model = None
        self.image_path = None
        self.model_path = None
        self.current_pixmap = None
        self.sliced_pred_result = None
        self._active_operation = None
        self._thread = None
        self._worker = None
        self._pending_path = None

        self._restore_settings()
        self.deviceCombo.currentIndexChanged.connect(self._model_settings_changed)
        self.confidenceInput.valueChanged.connect(self._model_settings_changed)
        self._update_controls()
        self.statusLabel.setText('Ready')

    def _restore_settings(self):
        geometry = self.settings.value('windowGeometry')
        if geometry:
            self.restoreGeometry(geometry)
        self.sliceHeightInput.setValue(
            self.settings.value('sliceHeight', 1080, type=int)
        )
        self.sliceWidthInput.setValue(
            self.settings.value('sliceWidth', 1080, type=int)
        )
        self.overlapHeightInput.setValue(
            self.settings.value('overlapHeight', 0.2, type=float)
        )
        self.overlapWidthInput.setValue(
            self.settings.value('overlapWidth', 0.2, type=float)
        )
        self.confidenceInput.setValue(
            self.settings.value('confidence', 0.5, type=float)
        )
        device = self.settings.value('device', 'auto')
        index = self.deviceCombo.findData(device)
        self.deviceCombo.setCurrentIndex(max(0, index))

    def _save_settings(self):
        self.settings.setValue('windowGeometry', self.saveGeometry())
        self.settings.setValue('sliceHeight', self.sliceHeightInput.value())
        self.settings.setValue('sliceWidth', self.sliceWidthInput.value())
        self.settings.setValue('overlapHeight', self.overlapHeightInput.value())
        self.settings.setValue('overlapWidth', self.overlapWidthInput.value())
        self.settings.setValue('confidence', self.confidenceInput.value())
        self.settings.setValue('device', self.deviceCombo.currentData())

    def _last_directory(self, key):
        saved = self.settings.value(key, str(PROJECT_ROOT))
        return saved if Path(saved).exists() else str(PROJECT_ROOT)

    def _set_busy(self, operation, status):
        self._active_operation = operation
        self.statusLabel.setText(status)
        self._update_controls()

    def _finish_operation(self, status):
        self._active_operation = None
        self.statusLabel.setText(status)
        self._update_controls()

    def _update_controls(self):
        busy = self._active_operation is not None or self._thread is not None
        self.uploadButton.setEnabled(not busy)
        self.modelLoadButton.setEnabled(not busy)
        self.deviceCombo.setEnabled(not busy)
        self.confidenceInput.setEnabled(not busy)
        self.detectButton.setEnabled(
            not busy and self.image_path is not None and self.detection_model is not None
        )
        self.cancelButton.setEnabled(self._active_operation == 'detection')
        self.exportButton.setEnabled(not busy and self.sliced_pred_result is not None)
        has_image = self.current_pixmap is not None and not self.current_pixmap.isNull()
        self.zoomOutButton.setEnabled(has_image)
        self.zoomInButton.setEnabled(has_image)
        self.actualSizeButton.setEnabled(has_image)
        self.fitImageButton.setEnabled(has_image)

    def _launch_worker(self, worker, start_method, terminal_signals):
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(start_method)
        for signal in terminal_signals:
            signal.connect(thread.quit)
            signal.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(lambda: self._clear_thread(thread))
        self._thread = thread
        self._worker = worker
        thread.start()

    def _clear_thread(self, thread):
        if self._thread is thread:
            self._thread = None
            self._worker = None
        self._update_controls()

    def _show_error(self, title, message):
        logger.error('%s: %s', title, message)
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self._finish_operation(f'{title}: {message}')
        QMessageBox.critical(self, title, message)

    def _clear_results(self):
        self.sliced_pred_result = None
        self.summaryOverlay.hide()
        self.imageView.clear_detections()
        self.overlayToggle.setEnabled(False)
        self.overlayToggle.setChecked(True)
        self.resultsLabel.setText('No detection results')
        self.summaryCountLabel.setText('— patches')
        self.summaryAreaLabel.setText('Weed area: —')
        self.summaryCoverageLabel.setText('Image coverage: —')
        self.summaryHighLabel.setText('High (≥80%): —')
        self.summaryMediumLabel.setText('Medium (60–79%): —')
        self.summaryLowerLabel.setText('Lower (<60%): —')
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)

    def _model_settings_changed(self):
        if self.detection_model is not None and self._active_operation is None:
            self.detection_model = None
            self.modelPathLabel.setText('Settings changed - reload the model')
            self._clear_results()
            self._update_controls()

    def upload_image(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            'Open GeoTIFF',
            self._last_directory('lastImageDirectory'),
            'TIFF images (*.tif *.tiff)',
        )
        if not file_name:
            return

        from src.workers.image_worker import ImageUploadWorker

        self.settings.setValue('lastImageDirectory', str(Path(file_name).parent))
        self._pending_path = file_name
        self._set_busy(
            'image',
            f'Loading image preview at 1/{PREVIEW_DOWNSAMPLE_FACTOR} resolution...'
        )
        self.progressBar.setRange(0, 0)
        worker = ImageUploadWorker(file_name)
        worker.imageLoaded.connect(self._on_image_loaded)
        worker.error.connect(self._on_image_error)
        self._launch_worker(
            worker,
            worker.load_image,
            [worker.imageLoaded, worker.error],
        )

    def _on_image_loaded(self, image, original_width, original_height):
        self.image_path = self._pending_path
        self._pending_path = None
        self.current_pixmap = QPixmap.fromImage(image)
        self.imagePathLabel.setText(
            f'{Path(self.image_path).name}\n'
            f'Original: {original_width:,} x {original_height:,}\n'
            f'Preview: {image.width():,} x {image.height():,} '
            f'({PREVIEW_DOWNSAMPLE_FACTOR}x downsample)'
        )
        self._clear_results()
        self.imageView.set_image(self.current_pixmap)
        self._finish_operation('Image preview loaded')

    def _on_image_error(self, message):
        self._pending_path = None
        self._show_error('Image Load Error', message)

    def load_model(self):
        model_path, _ = QFileDialog.getOpenFileName(
            self,
            'Open YOLO Model',
            self._last_directory('lastModelDirectory'),
            'PyTorch models (*.pt)',
        )
        if not model_path:
            return

        self.settings.setValue('lastModelDirectory', str(Path(model_path).parent))
        self._pending_path = model_path
        self._set_busy('model', 'Loading model...')
        self.progressBar.setRange(0, 0)
        from src.workers.model_uploader import ModelUploadWorker

        worker = ModelUploadWorker(
            model_path,
            confidence_threshold=self.confidenceInput.value(),
            device_preference=self.deviceCombo.currentData(),
        )
        worker.modelLoaded.connect(self._on_model_loaded)
        worker.error.connect(self._on_model_error)
        self._launch_worker(
            worker,
            worker.load_model,
            [worker.modelLoaded, worker.error],
        )

    def _on_model_loaded(self, model, device):
        self.detection_model = model
        self.model_path = self._pending_path
        self._pending_path = None
        self.modelPathLabel.setText(f'{Path(self.model_path).name}\nDevice: {device}')
        self._clear_results()
        self._finish_operation(f'Model loaded on {device}')

    def _on_model_error(self, message):
        self._pending_path = None
        self._show_error('Model Load Error', message)

    def run_detection(self):
        if self.image_path is None or self.detection_model is None:
            QMessageBox.warning(self, 'Detection', 'Load an image and model first.')
            return

        self._clear_results()
        self._set_busy('detection', 'Preparing image slices...')
        self.progressBar.setRange(0, 0)
        from src.workers.detect_worker import DetectWorker

        worker = DetectWorker(
            image_path=self.image_path,
            detection_model=self.detection_model,
            slice_height=self.sliceHeightInput.value(),
            slice_width=self.sliceWidthInput.value(),
            overlap_height_ratio=self.overlapHeightInput.value(),
            overlap_width_ratio=self.overlapWidthInput.value(),
        )
        worker.progress.connect(self._on_detection_progress)
        worker.statusChanged.connect(self.statusLabel.setText)
        worker.finished.connect(self._on_detection_finished)
        worker.cancelled.connect(self._on_detection_cancelled)
        worker.error.connect(self._on_detection_error)
        self._launch_worker(
            worker,
            worker.run,
            [worker.finished, worker.cancelled, worker.error],
        )

    def _on_detection_progress(self, current_slice, total_slices):
        self.progressBar.setRange(0, total_slices)
        self.progressBar.setValue(current_slice)

    def _on_detection_finished(self, result):
        self.sliced_pred_result = result
        count = len(result.object_prediction_list)
        self.imageView.set_detections(
            result.object_prediction_list, result.image_width, result.image_height,
        )
        self.overlayToggle.setChecked(True)
        self.overlayToggle.setEnabled(count > 0)
        self.resultsLabel.setText(f'{count:,} detections shown; ready to export')
        summary = result.summary
        if summary is not None:
            noun = 'patch' if summary.count == 1 else 'patches'
            self.summaryCountLabel.setText(f'{summary.count:,} {noun}')
            if summary.area_m2 is None:
                self.summaryAreaLabel.setText('Weed area: unavailable (no usable map coordinates)')
            elif summary.area_m2 >= 10_000:
                self.summaryAreaLabel.setText(f'Estimated weed area: {summary.area_m2 / 10_000:,.2f} ha')
            else:
                self.summaryAreaLabel.setText(f'Estimated weed area: {summary.area_m2:,.1f} m²')
            self.summaryCoverageLabel.setText(
                f'Image coverage: {summary.coverage_percent:.3f}%'
            )
            self.summaryHighLabel.setText(f'High (≥80%): {summary.high_confidence:,}')
            self.summaryMediumLabel.setText(f'Medium (60–79%): {summary.medium_confidence:,}')
            self.summaryLowerLabel.setText(f'Lower (<60%): {summary.lower_confidence:,}')
        self.summaryOverlay.show()
        self.summaryOverlay.layout().activate()
        self.summaryOverlay.adjustSize()
        self.imageView.position_summary_widget()
        if self.progressBar.maximum() > 0:
            self.progressBar.setValue(self.progressBar.maximum())
        self._finish_operation(f'Detection complete - {count:,} objects found')

    def _on_detection_clicked(self, prediction, position):
        x1, y1, x2, y2 = prediction.bbox.to_xyxy()
        area = prediction.to_coco_prediction().json.get('area')
        if area is None:
            area = (x2 - x1) * (y2 - y1)
        self.imageView.show_detection_popup(
            f'{prediction.category.name}\n'
            f'Confidence: {prediction.score.value:.1%}\n'
            f'Patch area: {area:,.0f} px²\n'
            f'Bounds: {x2 - x1:,.0f} × {y2 - y1:,.0f} px',
            position,
        )

    def cancel_detection(self):
        if (
            self._active_operation == 'detection'
            and self._worker is not None
            and hasattr(self._worker, 'request_cancel')
        ):
            self._worker.request_cancel()
            self.cancelButton.setEnabled(False)
            self.statusLabel.setText('Cancellation requested; finishing the current slice...')

    def _on_detection_cancelled(self):
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(0)
        self._finish_operation('Detection cancelled')

    def _on_detection_error(self, message):
        self._show_error('Detection Error', message)

    def display_result(self):
        if self.sliced_pred_result is None:
            QMessageBox.warning(self, 'Export', 'Run detection before exporting results.')
            return

        export_directory = QFileDialog.getExistingDirectory(
            self,
            'Select Result Directory',
            self._last_directory('lastExportDirectory'),
        )
        if not export_directory:
            return

        self.settings.setValue('lastExportDirectory', export_directory)
        self._set_busy('export', 'Exporting prediction visualization...')
        self.progressBar.setRange(0, 0)
        from src.workers.export_worker import ExportWorker

        worker = ExportWorker(self.sliced_pred_result, export_directory)
        worker.finished.connect(self._on_export_finished)
        worker.error.connect(self._on_export_error)
        self._launch_worker(
            worker,
            worker.export,
            [worker.finished, worker.error],
        )

    def _on_export_finished(self, output_path):
        self.resultsLabel.setText(
            f'{len(self.sliced_pred_result.object_prediction_list):,} detections shown\n'
            f'Exported to {Path(output_path).parent}'
        )
        self.progressBar.setRange(0, 100)
        self.progressBar.setValue(100)
        self._finish_operation(f'Results exported to {output_path}')
        QMessageBox.information(self, 'Export Complete', f'Results saved to:\n{output_path}')

    def _on_export_error(self, message):
        self._show_error('Export Error', message)

    def closeEvent(self, event: QCloseEvent):
        if self._thread is not None and self._thread.isRunning():
            if self._active_operation == 'detection':
                self.cancel_detection()
                message = 'Detection is stopping. Close the app after cancellation completes.'
            else:
                message = 'Please wait for the current operation to finish before closing.'
            QMessageBox.information(self, 'Operation in Progress', message)
            event.ignore()
            return
        self._save_settings()
        super().closeEvent(event)


def main():
    configure_logging()
    app = QApplication(sys.argv)
    app.setApplicationName('Weed Detection App')
    app.setOrganizationName('WeedDetectionApp')
    apply_app_theme(app)
    window = WeedDetectionApp()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
