'''High-contrast visual theme for the desktop application.'''

from qt_material import apply_stylesheet


_APP_STYLESHEET = r'''
QMainWindow,
QWidget#centralContainer,
QWidget#controlsPanel,
QWidget#imagePanel {
    background-color: #F1F5F9;
    color: #1E293B;
}

QScrollArea#controlsScroll {
    background-color: #F1F5F9;
    border: none;
}

QScrollArea#controlsScroll > QWidget > QWidget {
    background-color: #F1F5F9;
}

QGroupBox {
    background-color: #FFFFFF;
    color: #334155;
    border: 1px solid #CBD5E1;
    border-radius: 8px;
    margin-top: 12px;
    padding: 14px 10px 10px 10px;
    font-weight: 600;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
    background-color: #FFFFFF;
    color: #0F766E;
}

QFrame#summaryOverlay {
    background-color: rgba(234, 247, 244, 225);
    border: 1px solid #0F766E;
    border-radius: 8px;
}

QWidget#summaryBody {
    background-color: transparent;
}

QLabel#summaryTitle {
    color: #115E59;
    font-size: 11px;
    font-weight: 700;
    border: none;
}

QToolButton#summaryCollapse {
    color: #115E59;
    background-color: #D1EAE4;
    border: none;
    border-radius: 9px;
    font-weight: 700;
}

QToolButton#summaryCollapse:hover {
    background-color: #B8DDD4;
}

QLabel#summaryCount {
    color: #115E59;
    font-size: 20px;
    font-weight: 700;
}

QLabel#summaryNote {
    color: #475569;
    font-size: 11px;
}

QFrame#detectionPopup {
    background-color: #FFFFFF;
    border: 2px solid #0F766E;
    border-radius: 8px;
}

QLabel#detectionPopupTitle {
    color: #115E59;
    font-weight: 700;
    font-size: 13px;
    border: none;
}

QLabel#detectionPopupText {
    color: #1E293B;
    border: none;
}

QToolButton#detectionPopupClose {
    color: #334155;
    background-color: #E2E8F0;
    border: none;
    border-radius: 9px;
    min-width: 18px;
    min-height: 18px;
}

QToolButton#detectionPopupClose:hover {
    background-color: #CBD5E1;
}

QLabel {
    background-color: transparent;
    color: #334155;
}

QLabel#imageHint {
    color: #64748B;
}

QLabel#zoomLabel {
    color: #334155;
    font-weight: 600;
}

QPushButton {
    min-height: 34px;
    padding: 0 14px;
    border-radius: 6px;
    font-weight: 600;
}

QPushButton[variant="primary"] {
    background-color: #0F766E;
    color: #FFFFFF;
    border: 1px solid #0F766E;
}

QPushButton[variant="primary"]:hover {
    background-color: #115E59;
    border-color: #115E59;
}

QPushButton[variant="primary"]:pressed {
    background-color: #134E4A;
    border-color: #134E4A;
}

QPushButton[variant="secondary"] {
    background-color: #E2E8F0;
    color: #1E293B;
    border: 1px solid #94A3B8;
}

QPushButton[variant="secondary"]:hover {
    background-color: #CBD5E1;
    border-color: #64748B;
}

QPushButton[variant="secondary"]:pressed {
    background-color: #B8C4D3;
    border-color: #475569;
}

QPushButton[variant="danger"] {
    background-color: #B91C1C;
    color: #FFFFFF;
    border: 1px solid #B91C1C;
}

QPushButton[variant="danger"]:hover {
    background-color: #991B1B;
    border-color: #991B1B;
}

QPushButton[variant="danger"]:pressed {
    background-color: #7F1D1D;
    border-color: #7F1D1D;
}

QPushButton:disabled,
QPushButton[variant="primary"]:disabled,
QPushButton[variant="secondary"]:disabled,
QPushButton[variant="danger"]:disabled {
    background-color: #CBD5E1;
    color: #475569;
    border: 1px solid #94A3B8;
}

QComboBox,
QSpinBox,
QDoubleSpinBox {
    min-height: 28px;
    padding: 2px 8px;
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #94A3B8;
    border-radius: 5px;
    selection-background-color: #0F766E;
    selection-color: #FFFFFF;
}

QComboBox:hover,
QSpinBox:hover,
QDoubleSpinBox:hover {
    border-color: #0F766E;
}

QComboBox:focus,
QSpinBox:focus,
QDoubleSpinBox:focus {
    border: 2px solid #0F766E;
}

QComboBox:disabled,
QSpinBox:disabled,
QDoubleSpinBox:disabled {
    background-color: #E2E8F0;
    color: #475569;
    border-color: #CBD5E1;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    color: #1E293B;
    border: 1px solid #94A3B8;
    selection-background-color: #0F766E;
    selection-color: #FFFFFF;
}

QProgressBar {
    min-height: 12px;
    background-color: #E2E8F0;
    color: #1E293B;
    border: 1px solid #CBD5E1;
    border-radius: 5px;
    text-align: center;
}

QProgressBar::chunk {
    background-color: #14B8A6;
    border-radius: 4px;
}

QGraphicsView#imageView {
    background-color: #202225;
    border: 1px solid #475569;
    border-radius: 6px;
}

QScrollBar:vertical {
    width: 10px;
    margin: 0;
    background-color: #E2E8F0;
}

QScrollBar::handle:vertical {
    min-height: 28px;
    background-color: #94A3B8;
    border-radius: 5px;
}

QScrollBar::handle:vertical:hover {
    background-color: #64748B;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QToolTip {
    background-color: #1E293B;
    color: #FFFFFF;
    border: 1px solid #475569;
    padding: 5px;
}
'''


def apply_app_theme(app):
    '''Apply qt-material and the app-specific accessible color overrides.'''
    apply_stylesheet(
        app,
        theme='light_teal.xml',
        extra={
            'density_scale': '-1',
            'font_family': 'Segoe UI',
            'primaryColor': '#0F766E',
            'secondaryColor': '#F1F5F9',
        },
    )
    app.setStyleSheet(f'{app.styleSheet()}\n{_APP_STYLESHEET}')
