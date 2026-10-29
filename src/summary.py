'''Coverage and confidence statistics for a completed detection run.'''

import logging
import math
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


@dataclass(frozen=True)
class PatchDetails:
    latitude: float | None
    longitude: float | None
    area_m2: float | None


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


def _ground_area_m2(geometry, transform, crs):
    if crs is None or transform is None:
        return None
    if geometry.is_empty:
        return 0.0
    try:
        # EPSG:6933 preserves area when the source CRS uses degrees.
        world_shape = affine_transform(
            geometry,
            [transform.a, transform.b, transform.d,
             transform.e, transform.c, transform.f],
        )
        from rasterio.warp import transform_geom
        return shape(transform_geom(crs, 'EPSG:6933', mapping(world_shape))).area
    except Exception:
        logger.exception('Could not calculate geographic detection area')
        return None


def describe_patch(prediction, transform=None, crs=None):
    '''Return a point within the mask in GPS coordinates and its ground area.'''
    geometry = _prediction_shape(prediction)
    area_m2 = _ground_area_m2(geometry, transform, crs)
    if crs is None or transform is None or geometry.is_empty:
        return PatchDetails(None, None, area_m2)
    try:
        point = geometry.centroid
        if not geometry.covers(point):
            point = geometry.representative_point()
        x, y = transform @ (point.x, point.y)
        from rasterio.warp import transform as transform_coordinates
        longitude, latitude = transform_coordinates(crs, 'EPSG:4326', [x], [y])
        lat, lon = latitude[0], longitude[0]
        if not math.isfinite(lat) or not math.isfinite(lon):
            raise ValueError('Invalid geographic coordinates')
        return PatchDetails(lat, lon, area_m2)
    except Exception:
        logger.exception('Could not calculate detection location')
        return PatchDetails(None, None, area_m2)


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
    area_m2 = _ground_area_m2(covered, transform, crs)

    return DetectionSummary(
        count=len(predictions),
        covered_pixels=pixel_area,
        coverage_percent=coverage_percent,
        area_m2=area_m2,
        high_confidence=counts[0],
        medium_confidence=counts[1],
        lower_confidence=counts[2],
    )
