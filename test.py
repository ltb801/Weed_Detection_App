'''Fast smoke tests for the application shell and utility behavior.'''

import os
import unittest
from unittest.mock import patch

import numpy as np

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from main import WeedDetectionApp, resolve_device
from src.ui.image_view import ZoomableImageView
from src.workers.image_worker import _downsampled_size, _to_uint8


class WeedDetectionSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_cpu_device_selection(self):
        self.assertEqual(resolve_device('cpu'), 'cpu')

    @patch('src.device._cuda_is_available', return_value=False)
    def test_auto_device_falls_back_to_cpu(self, _):
        self.assertEqual(resolve_device('auto'), 'cpu')

    @patch('src.device._cuda_is_available', return_value=False)
    def test_explicit_unavailable_cuda_is_rejected(self, _):
        with self.assertRaises(ValueError):
            resolve_device('cuda:0')

    def test_preview_scaling_produces_bytes(self):
        source = np.array([[0, 1000], [2000, 3000]], dtype=np.uint16)
        result = _to_uint8(source)
        self.assertEqual(result.dtype, np.uint8)
        self.assertEqual(result.shape, source.shape)

    def test_preview_dimensions_are_downsampled_by_two(self):
        self.assertEqual(_downsampled_size(1000, 600), (500, 300))
        self.assertEqual(_downsampled_size(1001, 601), (501, 301))

    def test_image_view_zoom_controls(self):
        view = ZoomableImageView()
        view.resize(400, 300)
        view.set_image(QPixmap(200, 100))
        view.actual_size()
        self.assertAlmostEqual(view.transform().m11(), 1.0)
        view.zoom_in()
        self.assertAlmostEqual(view.transform().m11(), 1.25)
        view.zoom_out()
        self.assertAlmostEqual(view.transform().m11(), 1.0)

    def test_initial_ui_state(self):
        window = WeedDetectionApp()
        self.assertFalse(window.detectButton.isEnabled())
        self.assertFalse(window.exportButton.isEnabled())
        self.assertFalse(window.overlayToggle.isEnabled())
        self.assertFalse(window.summaryOverlay.isVisible())
        self.assertFalse(window.cancelButton.isEnabled())
        self.assertFalse(window.zoomInButton.isEnabled())
        self.assertFalse(window.zoomOutButton.isEnabled())
        window.close()

    def test_detection_overlay_can_be_inspected_and_hidden(self):
        from sahi.prediction import ObjectPrediction
        from src.summary import DetectionSummary
        from src.workers.detect_worker import DetectionResult

        window = WeedDetectionApp()
        window.show()
        window.current_pixmap = QPixmap(100, 50)
        window.imageView.set_image(window.current_pixmap)
        prediction = ObjectPrediction(
            bbox=[20, 20, 40, 40], category_id=0, category_name='weed',
            segmentation=[[20, 20, 40, 20, 40, 40, 20, 40]],
            score=0.8, full_shape=[100, 200],
        )
        summary = DetectionSummary(1, 400, 2, 10.0, 1, 0, 0)
        window._on_detection_finished(DetectionResult('example.tif', 200, 100, [prediction], summary))
        self.assertTrue(window.overlayToggle.isEnabled())
        self.assertEqual(len(window.imageView._detections), 1)
        self.assertIn('1 patch', window.summaryCountLabel.text())
        self.assertIn('10.0 m', window.summaryAreaLabel.text())

        self.app.processEvents()
        self.assertIs(window.summaryOverlay.parent(), window.imageView.viewport())
        self.assertTrue(window.summaryOverlay.isVisible())
        self.assertGreater(window.summaryOverlay.x(), window.imageView.viewport().width() // 2)
        overlay_position = window.summaryOverlay.pos()
        window.imageView.zoom_in()
        self.assertEqual(window.summaryOverlay.pos(), overlay_position)
        self.assertTrue(window.summaryOverlay.isVisible())
        expanded_height = window.summaryOverlay.height()
        window.summaryCollapseButton.click()
        self.app.processEvents()
        self.assertLess(window.summaryOverlay.height(), expanded_height)
        window.summaryCollapseButton.click()
        self.app.processEvents()
        point = window.imageView.mapFromScene(QPointF(15, 15))
        QTest.mouseClick(window.imageView.viewport(), Qt.LeftButton, pos=point)
        self.assertTrue(window.imageView._popup.isVisible())
        self.assertIn('80.0%', window.imageView._popup_text.text())
        self.assertIn('px²', window.imageView._popup_text.text())

        window.overlayToggle.setChecked(False)
        self.assertFalse(window.imageView._detections[0][0].isVisible())
        self.assertFalse(window.imageView._popup.isVisible())
        window.close()

    def test_summary_counts_overlapping_patches_once(self):
        from rasterio.transform import from_origin
        from sahi.prediction import ObjectPrediction
        from src.summary import summarize_detections

        predictions = [
            ObjectPrediction(bbox=[10, 10, 20, 20], category_id=0,
                             category_name='weed', score=0.9),
            ObjectPrediction(bbox=[15, 10, 25, 20], category_id=0,
                             category_name='weed', score=0.7),
        ]
        summary = summarize_detections(
            predictions, 100, 100, from_origin(0, 100, 1, 1), 'EPSG:3857',
        )
        self.assertEqual(summary.count, 2)
        self.assertAlmostEqual(summary.covered_pixels, 150)
        self.assertAlmostEqual(summary.coverage_percent, 1.5)
        self.assertEqual((summary.high_confidence, summary.medium_confidence,
                          summary.lower_confidence), (1, 1, 0))
        self.assertGreater(summary.area_m2, 0)


if __name__ == '__main__':
    unittest.main()
