'''Zoomable and pannable image viewer used by the main window.'''

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (
    QFrame, QGraphicsPathItem, QGraphicsPixmapItem, QGraphicsScene,
    QGraphicsView, QHBoxLayout, QLabel, QToolButton, QVBoxLayout,
)


class ZoomableImageView(QGraphicsView):
    zoomChanged = Signal(int)
    detectionClicked = Signal(object, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self._pixmap_item = QGraphicsPixmapItem()
        self._scene.addItem(self._pixmap_item)
        self.setScene(self._scene)
        self.setBackgroundBrush(QBrush(QColor('#202124')))
        self.setFrameShape(QGraphicsView.StyledPanel)
        self.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setMinimumSize(480, 360)
        self._fit_mode = True
        self._has_image = False
        self._detections = []
        self._selected_item = None
        self._press_position = None
        self._summary_widget = None
        self._popup = QFrame(self.viewport())
        self._popup.setObjectName('detectionPopup')
        popup_layout = QVBoxLayout(self._popup)
        popup_layout.setContentsMargins(12, 10, 12, 10)
        popup_layout.setSpacing(6)
        popup_header = QHBoxLayout()
        popup_title = QLabel('Weed patch')
        popup_title.setObjectName('detectionPopupTitle')
        popup_close = QToolButton()
        popup_close.setText('×')
        popup_close.setAccessibleName('Close weed patch details')
        popup_close.setObjectName('detectionPopupClose')
        popup_close.setFixedSize(22, 22)
        popup_close.clicked.connect(self._popup.hide)
        popup_header.addWidget(popup_title)
        popup_header.addStretch(1)
        popup_header.addWidget(popup_close)
        self._popup_text = QLabel()
        self._popup_text.setObjectName('detectionPopupText')
        self._popup_text.setWordWrap(True)
        popup_layout.addLayout(popup_header)
        popup_layout.addWidget(self._popup_text)
        self._popup.hide()

    def set_summary_widget(self, widget):
        self._summary_widget = widget
        widget.setParent(self.viewport())
        self.position_summary_widget()

    def position_summary_widget(self):
        if getattr(self, '_summary_widget', None) is None:
            return
        self._summary_widget.adjustSize()
        self._summary_widget.move(
            max(8, self.viewport().width() - self._summary_widget.width() - 12), 12,
        )
        self._summary_widget.raise_()

    def set_image(self, pixmap: QPixmap):
        self.clear_detections()
        self._pixmap_item.setPixmap(pixmap)
        self._scene.setSceneRect(self._pixmap_item.boundingRect())
        self._has_image = not pixmap.isNull()
        self.fit_to_window()

    def clear_image(self):
        self.clear_detections()
        self._pixmap_item.setPixmap(QPixmap())
        self._scene.setSceneRect(0, 0, 1, 1)
        self._has_image = False
        self.resetTransform()
        self.zoomChanged.emit(100)

    def clear_detections(self):
        self._popup.hide()
        for item, _ in self._detections:
            self._scene.removeItem(item)
        self._detections.clear()
        self._selected_item = None

    def set_detections(self, predictions, source_width, source_height):
        '''Draw source-image polygons in preview coordinates.'''
        self.clear_detections()
        if not self._has_image or source_width <= 0 or source_height <= 0:
            return
        scale_x = self._pixmap_item.pixmap().width() / source_width
        scale_y = self._pixmap_item.pixmap().height() / source_height
        for prediction in predictions:
            path = QPainterPath()
            if prediction.mask:
                for polygon in prediction.mask.segmentation:
                    if len(polygon) < 6 or len(polygon) % 2:
                        continue
                    path.moveTo(polygon[0] * scale_x, polygon[1] * scale_y)
                    for index in range(2, len(polygon), 2):
                        path.lineTo(polygon[index] * scale_x, polygon[index + 1] * scale_y)
                    path.closeSubpath()
            if path.isEmpty():
                x1, y1, x2, y2 = prediction.bbox.to_xyxy()
                path.addRect(x1 * scale_x, y1 * scale_y,
                             (x2 - x1) * scale_x, (y2 - y1) * scale_y)
            item = QGraphicsPathItem(path)
            item.setPen(self._detection_pen(False))
            item.setBrush(QBrush(QColor(255, 193, 7, 65)))
            item.setZValue(1)
            item.setAcceptedMouseButtons(Qt.NoButton)
            self._scene.addItem(item)
            self._detections.append((item, prediction))

    @staticmethod
    def _detection_pen(selected):
        pen = QPen(QColor('#00E5FF' if selected else '#FFC107'))
        pen.setWidth(3 if selected else 2)
        pen.setCosmetic(True)
        return pen

    def set_detections_visible(self, visible):
        if not visible:
            self._popup.hide()
        for item, _ in self._detections:
            item.setVisible(visible)

    def show_detection_popup(self, text, position):
        self._popup_text.setText(text)
        self._popup.setFixedWidth(230)
        self._popup.adjustSize()
        width = self._popup.width()
        height = self._popup.height()
        viewport = self.viewport().rect()
        x = position.x() + 12
        y = position.y() + 12
        if x + width > viewport.width() - 8:
            x = position.x() - width - 12
        if y + height > viewport.height() - 8:
            y = position.y() - height - 12
        self._popup.move(max(8, min(x, viewport.width() - width - 8)),
                         max(8, min(y, viewport.height() - height - 8)))
        self._popup.raise_()
        self._popup.show()

    def mousePressEvent(self, event):
        self._popup.hide()
        self._press_position = event.position().toPoint() if event.button() == Qt.LeftButton else None
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        clicked = (
            event.button() == Qt.LeftButton
            and self._press_position is not None
            and (event.position().toPoint() - self._press_position).manhattanLength() <= 4
        )
        self._press_position = None
        super().mouseReleaseEvent(event)
        if clicked:
            scene_position = self.mapToScene(event.position().toPoint())
            for item, prediction in reversed(self._detections):
                if item.isVisible() and item.path().contains(scene_position):
                    if self._selected_item is not None:
                        self._selected_item.setPen(self._detection_pen(False))
                    item.setPen(self._detection_pen(True))
                    self._selected_item = item
                    self.detectionClicked.emit(prediction, event.position().toPoint())
                    break

    def fit_to_window(self):
        if not self._has_image:
            return
        self._popup.hide()
        self._fit_mode = True
        self.resetTransform()
        self.fitInView(self._pixmap_item, Qt.KeepAspectRatio)
        self._emit_zoom()

    def actual_size(self):
        if not self._has_image:
            return
        self._popup.hide()
        self._fit_mode = False
        self.resetTransform()
        self.centerOn(self._pixmap_item)
        self._emit_zoom()

    def zoom_in(self):
        self._zoom(1.25)

    def zoom_out(self):
        self._zoom(0.8)

    def _zoom(self, factor):
        if not self._has_image:
            return
        current_scale = self.transform().m11()
        target_scale = current_scale * factor
        if 0.005 <= target_scale <= 32.0:
            self._popup.hide()
            self._fit_mode = False
            self.scale(factor, factor)
            self._emit_zoom()

    def _emit_zoom(self):
        self.zoomChanged.emit(max(1, round(self.transform().m11() * 100)))

    def wheelEvent(self, event):
        if not self._has_image:
            super().wheelEvent(event)
            return
        self._zoom(1.25 if event.angleDelta().y() > 0 else 0.8)
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if self._has_image:
            self.fit_to_window()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, '_popup'):
            self._popup.hide()
        self.position_summary_widget()
        if self._fit_mode:
            self.fit_to_window()
