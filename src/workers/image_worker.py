'''Background image-preview loader.'''

import logging

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from src.config import PREVIEW_DOWNSAMPLE_FACTOR

logger = logging.getLogger(__name__)


def _to_uint8(array):
    '''Scale integer or floating-point image data into displayable bytes.'''
    import numpy as np

    if array.dtype == np.uint8:
        return np.ascontiguousarray(array)

    result = np.zeros(array.shape, dtype=np.uint8)
    channels = 1 if array.ndim == 2 else array.shape[2]
    for channel in range(channels):
        source = array if array.ndim == 2 else array[:, :, channel]
        finite = source[np.isfinite(source)]
        if finite.size == 0:
            scaled = np.zeros(source.shape, dtype=np.uint8)
        else:
            low, high = np.percentile(finite, (2, 98))
            if high <= low:
                low, high = float(finite.min()), float(finite.max())
            if high <= low:
                scaled = np.zeros(source.shape, dtype=np.uint8)
            else:
                scaled = np.clip(
                    (source - low) * 255.0 / (high - low), 0, 255
                ).astype(np.uint8)
        if array.ndim == 2:
            result = scaled
        else:
            result[:, :, channel] = scaled
    return np.ascontiguousarray(result)


def _downsampled_size(width, height, downsample_factor=PREVIEW_DOWNSAMPLE_FACTOR):
    '''Return dimensions reduced by an integer factor, retaining edge pixels.'''
    if downsample_factor < 1:
        raise ValueError('downsample_factor must be at least 1')
    return (
        max(1, (width + downsample_factor - 1) // downsample_factor),
        max(1, (height + downsample_factor - 1) // downsample_factor),
    )


def load_preview(file_path, downsample_factor=PREVIEW_DOWNSAMPLE_FACTOR):
    '''Read a preview at exactly 1/downsample_factor of the source dimensions.'''
    import rasterio
    from PIL import Image
    from rasterio.enums import Resampling

    try:
        with rasterio.open(file_path) as source:
            width, height = _downsampled_size(
                source.width, source.height, downsample_factor
            )
            if source.count >= 3:
                data = source.read(
                    [1, 2, 3],
                    out_shape=(3, height, width),
                    resampling=Resampling.bilinear,
                ).transpose(1, 2, 0)
                data = _to_uint8(data)
                image = QImage(
                    data.data, width, height, data.strides[0], QImage.Format_RGB888
                )
            else:
                data = source.read(
                    1,
                    out_shape=(height, width),
                    resampling=Resampling.bilinear,
                )
                data = _to_uint8(data)
                image = QImage(
                    data.data, width, height, data.strides[0], QImage.Format_Grayscale8
                )
            return image.copy(), source.width, source.height
    except rasterio.errors.RasterioError:
        logger.info('Rasterio could not read %s; falling back to Pillow', file_path)
        with Image.open(file_path) as source:
            original_size = source.size
            preview_size = _downsampled_size(
                source.width, source.height, downsample_factor
            )
            resampling = getattr(Image, 'Resampling', Image)
            source = source.convert('RGB').resize(preview_size, resampling.LANCZOS)
            data = source.tobytes('raw', 'RGB')
            image = QImage(
                data, source.width, source.height, source.width * 3, QImage.Format_RGB888
            )
            return image.copy(), original_size[0], original_size[1]


class ImageUploadWorker(QObject):
    imageLoaded = Signal(QImage, int, int)
    error = Signal(str)

    def __init__(self, file_path, downsample_factor=PREVIEW_DOWNSAMPLE_FACTOR):
        super().__init__()
        self.file_path = file_path
        self.downsample_factor = downsample_factor

    @Slot()
    def load_image(self):
        try:
            image, width, height = load_preview(
                self.file_path, self.downsample_factor
            )
            self.imageLoaded.emit(image, width, height)
        except Exception as exc:
            logger.exception('Image preview loading failed')
            self.error.emit(str(exc))
