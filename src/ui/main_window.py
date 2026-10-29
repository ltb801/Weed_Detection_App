'''Qt widget construction for the weed detection application.'''

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from .image_view import ZoomableImageView


class UI_MainWindow:
    def initUI(self, main_window):
        main_window.setWindowTitle('Weed Detection App')
        main_window.resize(1100, 700)

        icon_path = Path(__file__).resolve().parents[2] / 'data' / 'logo' / 'logo.png'
        if icon_path.exists():
            main_window.setWindowIcon(QIcon(str(icon_path)))

        container = QWidget()
        container.setObjectName('centralContainer')
        layout = QHBoxLayout(container)

        controls = QWidget()
        controls.setObjectName('controlsPanel')
        controls.setMaximumWidth(360)
        controls_layout = QVBoxLayout(controls)
        controls_layout.addWidget(self._create_image_group(main_window))
        controls_layout.addWidget(self._create_model_group(main_window))
        controls_layout.addWidget(self._create_detection_settings(main_window))
        controls_layout.addWidget(self._create_detection_group(main_window))
        controls_layout.addWidget(self._create_export_group(main_window))
        controls_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setObjectName('controlsScroll')
        scroll.setWidgetResizable(True)
        scroll.setWidget(controls)

        image_panel = QWidget()
        image_panel.setObjectName('imagePanel')
        image_layout = QVBoxLayout(image_panel)
        zoom_controls = QHBoxLayout()
        main_window.zoomOutButton = QPushButton('Zoom Out')
        main_window.zoomInButton = QPushButton('Zoom In')
        main_window.actualSizeButton = QPushButton('100%')
        main_window.fitImageButton = QPushButton('Fit')
        for button in (
            main_window.zoomOutButton,
            main_window.zoomInButton,
            main_window.actualSizeButton,
            main_window.fitImageButton,
        ):
            button.setProperty('variant', 'secondary')
        main_window.zoomLabel = QLabel('100%')
        main_window.zoomLabel.setObjectName('zoomLabel')
        main_window.overlayToggle = QCheckBox('Show detections')
        main_window.overlayToggle.setChecked(True)
        main_window.overlayToggle.setEnabled(False)
        zoom_controls.addWidget(main_window.zoomOutButton)
        zoom_controls.addWidget(main_window.zoomInButton)
        zoom_controls.addWidget(main_window.actualSizeButton)
        zoom_controls.addWidget(main_window.fitImageButton)
        zoom_controls.addStretch(1)
        zoom_controls.addWidget(main_window.overlayToggle)
        zoom_controls.addSpacing(10)
        zoom_controls.addWidget(main_window.zoomLabel)

        main_window.imageView = ZoomableImageView()
        main_window.imageView.setObjectName('imageView')
        main_window.summaryOverlay = self._create_summary_overlay(
            main_window, main_window.imageView.viewport(),
        )
        main_window.imageView.set_summary_widget(main_window.summaryOverlay)
        main_window.overlayToggle.toggled.connect(main_window.imageView.set_detections_visible)
        main_window.zoomOutButton.clicked.connect(main_window.imageView.zoom_out)
        main_window.zoomInButton.clicked.connect(main_window.imageView.zoom_in)
        main_window.actualSizeButton.clicked.connect(main_window.imageView.actual_size)
        main_window.fitImageButton.clicked.connect(main_window.imageView.fit_to_window)
        main_window.imageView.zoomChanged.connect(
            lambda value: main_window.zoomLabel.setText(f'{value}%')
        )
        image_hint = QLabel(
            'Mouse wheel: zoom  |  Drag: pan  |  Double-click: fit to window'
        )
        image_hint.setObjectName('imageHint')
        image_hint.setWordWrap(True)
        image_layout.addLayout(zoom_controls)
        image_layout.addWidget(main_window.imageView, 1)
        image_layout.addWidget(image_hint)

        layout.addWidget(scroll, 0)
        layout.addWidget(image_panel, 1)
        main_window.setCentralWidget(container)

    def _create_image_group(self, main_window):
        group = QGroupBox('1. Image')
        layout = QVBoxLayout(group)
        main_window.imagePathLabel = QLabel('No image selected')
        main_window.imagePathLabel.setWordWrap(True)
        main_window.uploadButton = QPushButton('Choose GeoTIFF...')
        main_window.uploadButton.setProperty('variant', 'primary')
        main_window.uploadButton.clicked.connect(main_window.upload_image)
        layout.addWidget(main_window.imagePathLabel)
        layout.addWidget(main_window.uploadButton)
        return group

    def _create_model_group(self, main_window):
        group = QGroupBox('2. Model')
        layout = QVBoxLayout(group)
        main_window.modelPathLabel = QLabel('No model selected')
        main_window.modelPathLabel.setWordWrap(True)
        form = QFormLayout()
        main_window.deviceCombo = QComboBox()
        main_window.deviceCombo.addItem('Automatic', 'auto')
        main_window.deviceCombo.addItem('CPU', 'cpu')
        main_window.deviceCombo.addItem('NVIDIA GPU', 'cuda:0')
        main_window.confidenceInput = QDoubleSpinBox()
        main_window.confidenceInput.setRange(0.01, 0.99)
        main_window.confidenceInput.setSingleStep(0.05)
        main_window.confidenceInput.setValue(0.5)
        form.addRow('Device:', main_window.deviceCombo)
        form.addRow('Confidence:', main_window.confidenceInput)
        main_window.modelLoadButton = QPushButton('Choose YOLO model...')
        main_window.modelLoadButton.setProperty('variant', 'primary')
        main_window.modelLoadButton.clicked.connect(main_window.load_model)
        layout.addWidget(main_window.modelPathLabel)
        layout.addLayout(form)
        layout.addWidget(main_window.modelLoadButton)
        return group

    def _create_detection_settings(self, main_window):
        group = QGroupBox('3. Slice settings')
        form = QFormLayout(group)
        main_window.sliceHeightInput = QSpinBox()
        main_window.sliceHeightInput.setRange(100, 5000)
        main_window.sliceHeightInput.setValue(1080)
        main_window.sliceWidthInput = QSpinBox()
        main_window.sliceWidthInput.setRange(100, 5000)
        main_window.sliceWidthInput.setValue(1080)
        main_window.overlapHeightInput = QDoubleSpinBox()
        main_window.overlapHeightInput.setRange(0.0, 0.9)
        main_window.overlapHeightInput.setSingleStep(0.05)
        main_window.overlapHeightInput.setValue(0.2)
        main_window.overlapWidthInput = QDoubleSpinBox()
        main_window.overlapWidthInput.setRange(0.0, 0.9)
        main_window.overlapWidthInput.setSingleStep(0.05)
        main_window.overlapWidthInput.setValue(0.2)
        form.addRow('Slice height:', main_window.sliceHeightInput)
        form.addRow('Slice width:', main_window.sliceWidthInput)
        form.addRow('Vertical overlap:', main_window.overlapHeightInput)
        form.addRow('Horizontal overlap:', main_window.overlapWidthInput)
        return group

    def _create_detection_group(self, main_window):
        group = QGroupBox('4. Detection')
        layout = QVBoxLayout(group)
        buttons = QHBoxLayout()
        main_window.detectButton = QPushButton('Run detection')
        main_window.detectButton.setProperty('variant', 'primary')
        main_window.detectButton.clicked.connect(main_window.run_detection)
        main_window.cancelButton = QPushButton('Cancel')
        main_window.cancelButton.setProperty('variant', 'danger')
        main_window.cancelButton.clicked.connect(main_window.cancel_detection)
        buttons.addWidget(main_window.detectButton)
        buttons.addWidget(main_window.cancelButton)
        main_window.progressBar = QProgressBar()
        main_window.progressBar.setRange(0, 100)
        main_window.progressBar.setValue(0)
        main_window.statusLabel = QLabel('Ready')
        main_window.statusLabel.setWordWrap(True)
        layout.addLayout(buttons)
        layout.addWidget(main_window.progressBar)
        layout.addWidget(main_window.statusLabel)
        return group

    def _create_export_group(self, main_window):
        group = QGroupBox('5. Results')
        layout = QVBoxLayout(group)
        main_window.resultsLabel = QLabel('No detection results')
        main_window.resultsLabel.setWordWrap(True)
        main_window.exportButton = QPushButton('Export results...')
        main_window.exportButton.setProperty('variant', 'primary')
        main_window.exportButton.clicked.connect(main_window.display_result)
        layout.addWidget(main_window.resultsLabel)
        layout.addWidget(main_window.exportButton)
        return group

    def _create_summary_overlay(self, main_window, parent):
        card = QFrame(parent)
        card.setObjectName('summaryOverlay')
        card.setFixedWidth(236)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(5)
        header = QHBoxLayout()
        title = QLabel('DETECTION SUMMARY')
        title.setObjectName('summaryTitle')
        collapse_button = QToolButton()
        collapse_button.setObjectName('summaryCollapse')
        collapse_button.setText('−')
        collapse_button.setToolTip('Collapse summary')
        collapse_button.setCheckable(True)
        collapse_button.setFixedSize(22, 22)
        header.addWidget(title)
        header.addStretch(1)
        header.addWidget(collapse_button)
        layout.addLayout(header)

        body = QWidget(card)
        body.setObjectName('summaryBody')
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(5)
        main_window.summaryBody = body

        main_window.summaryCountLabel = QLabel('— patches')
        main_window.summaryCountLabel.setObjectName('summaryCount')
        main_window.summaryAreaLabel = QLabel('Weed area: —')
        main_window.summaryCoverageLabel = QLabel('Image coverage: —')
        main_window.summaryConfidenceTitle = QLabel('Confidence bands')
        main_window.summaryHighLabel = QLabel('High (≥80%): —')
        main_window.summaryMediumLabel = QLabel('Medium (60–79%): —')
        main_window.summaryLowerLabel = QLabel('Lower (<60%): —')
        main_window.summaryNoteLabel = QLabel('Coverage is based on the image footprint.')
        main_window.summaryNoteLabel.setObjectName('summaryNote')
        main_window.summaryNoteLabel.setWordWrap(True)
        for label in (
            main_window.summaryCountLabel,
            main_window.summaryAreaLabel,
            main_window.summaryCoverageLabel,
            main_window.summaryConfidenceTitle,
            main_window.summaryHighLabel,
            main_window.summaryMediumLabel,
            main_window.summaryLowerLabel,
            main_window.summaryNoteLabel,
        ):
            body_layout.addWidget(label)

        legend = QHBoxLayout()
        for colour, caption in (('#FFC107', 'Detected'), ('#00A6BF', 'Selected')):
            swatch = QLabel()
            swatch.setFixedSize(12, 12)
            swatch.setStyleSheet(f'background-color: {colour}; border-radius: 2px;')
            legend.addWidget(swatch)
            legend.addWidget(QLabel(caption))
        legend.addStretch(1)
        body_layout.addLayout(legend)
        layout.addWidget(body)

        def set_collapsed(collapsed):
            body.setVisible(not collapsed)
            collapse_button.setText('+' if collapsed else '−')
            collapse_button.setToolTip('Expand summary' if collapsed else 'Collapse summary')
            card.adjustSize()
            main_window.imageView.position_summary_widget()

        collapse_button.toggled.connect(set_collapsed)
        main_window.summaryCollapseButton = collapse_button
        card.hide()
        return card
