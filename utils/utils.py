import rasterio


def get_middle_point(bbox):
    """
    Calculate the middle point of a bounding box.
    bbox: A list of [x, y, width, height], where x and y is the top-left corner of the bounding box.
    """
    x, y, width, height = bbox
    middle_x = x + width / 2
    middle_y = y + height / 2
    return middle_x, middle_y


def pixel_to_coords(geotiff_path, x, y):
    """
    Convert pixel coordinates to geographic coordinates using the geotransform of the GeoTIFF.
    geotiff_path: Path to the GeoTIFF file.
    x, y: Pixel coordinates.
    """
    with rasterio.open(geotiff_path) as src:
        # Transform coordinates with the dataset's affine transformation.
        affine = src.transform
        lon, lat = affine * (x, y)
        return (lon, lat)