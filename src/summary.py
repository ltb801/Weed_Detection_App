'''Coverage and confidence statistics for a completed detection run.'''

import logging
from dataclasses import dataclass

from shapely.affinity import affine_transform
from shapely.geometry import Polygon, box, mapping, shape
from shapely.ops import unary_union

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectionSummary:
    count: int
    covered_pixels: float
    coverage_percent: float
    area_m2: float | None
    high_confidence: int
    medium_confidence: int
    lower_confidence: int


def _prediction_shape(prediction):
    polygons = []
    if prediction.mask:
        for segment in prediction.mask.segmentation:
            if len(segment) < 6 or len(segment) % 2:
                continue
            polygon = Polygon(zip(segment[::2], segment[1::2]))
            if not polygon.is_valid:
                polygon = polygon.buffer(0)
            if not polygon.is_empty:
                polygons.append(polygon)
    if polygons:
        return unary_union(polygons)
    x1, y1, x2, y2 = prediction.bbox.to_xyxy()
    return box(x1, y1, x2, y2)


def summarize_detections(predictions, width, height, transform=None, crs=None):
    '''Union mask polygons, then measure their share of the image footprint.'''
    counts = [0, 0, 0]
    shapes = []
    for prediction in predictions:
        score = prediction.score.value
        counts[0 if score >= 0.8 else 1 if score >= 0.6 else 2] += 1
        shapes.append(_prediction_shape(prediction))

    covered = unary_union(shapes).intersection(box(0, 0, width, height)) if shapes else Polygon()
    pixel_area = covered.area
    coverage_percent = 100 * pixel_area / (width * height) if width and height else 0
    area_m2 = None
    if crs is not None and transform is not None:
        if covered.is_empty:
            area_m2 = 0.0
        else:
            try:
                # EPSG:6933 is an equal-area CRS; source pixels may be in degrees.
                world_shape = affine_transform(
                    covered,
                    [transform.a, transform.b, transform.d,
                     transform.e, transform.c, transform.f],
                )
                from rasterio.warp import transform_geom
                area_m2 = shape(transform_geom(crs, 'EPSG:6933', mapping(world_shape))).area
            except Exception:
                logger.exception('Could not calculate geographic detection area')

    return DetectionSummary(
        count=len(predictions),
        covered_pixels=pixel_area,
        coverage_percent=coverage_percent,
        area_m2=area_m2,
        high_confidence=counts[0],
        medium_confidence=counts[1],
        lower_confidence=counts[2],
    )
