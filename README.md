# Weed Detection App

A desktop application for running YOLOv8 weed detection on large GeoTIFF images. The app reads the raster in manageable windows, runs sliced inference, combines overlapping detections, displays the results over the image, and exports both a visualization and COCO-style detection data.

## Features

- Desktop interface built with PySide6
- Memory-bounded processing of large GeoTIFF files
- YOLOv8 inference through the bundled SAHI runtime
- Automatic CPU or NVIDIA GPU selection
- Configurable confidence, slice size, and slice overlap
- Zoomable and pannable image preview with detection overlays
- Weed count, confidence bands, image coverage, and estimated geographic area
- PNG visualization and JSON detection export
- Background processing with progress reporting and cancellation

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/ltb801/Weed_Detection_App.git
cd Weed_Detection_App
```

### 2. Install the dependencies

```bash
conda create -n weed_detection_app python=3.12 -y
conda activate weed_detection_app

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The normal installation is sufficient for CPU inference. To use an NVIDIA GPU, install the PyTorch build appropriate for your operating system, GPU driver, and CUDA environment. Use the command provided by the [official PyTorch installation selector](https://pytorch.org/get-started/locally/), then install the remaining requirements.

You can confirm that PyTorch detects the GPU with:

```bash
python -c "import torch; print(torch.cuda.is_available())"
```

## Running the app

With the virtual environment activated, run:

```bash
python main.py
```

The application writes diagnostic information to the terminal and to `logs/weed_detection.log`.

## Usage

1. Select **Choose GeoTIFF...** and open a `.tif` or `.tiff` image. Detection uses the first three raster bands as colour channels.
2. Select a device:
   - **Automatic** uses an NVIDIA GPU when CUDA is available and otherwise uses the CPU.
   - **CPU** always runs inference on the CPU.
   - **NVIDIA GPU** requires a CUDA-enabled PyTorch installation.
3. Set the confidence threshold, then select **Choose YOLO model...** and open your `.pt` checkpoint. If you change the device or confidence after loading the model, reload the model.
4. Adjust the slice settings if needed. The defaults are 1080 x 1080 pixels with 20% horizontal and vertical overlap.
5. Select **Run detection**. Progress is reported one raster window at a time, and a running operation can be cancelled after its current window completes.
6. Inspect the overlay and summary. Use the mouse wheel to zoom, drag to pan, or double-click to fit the image to the window. Select a detection to see its class, confidence, area, and bounds.
7. Select **Export results...** and choose an output directory.

The export directory will contain:

- `prediction_visual.png`: a bounded-size rendering of the image with detections
- `detections.json`: COCO-style annotations using coordinates from the full-resolution source image

## Choosing inference settings

- **Confidence threshold:** Lower values retain more possible detections but may increase false positives.
- **Slice width and height:** Smaller slices use less inference memory. The best size depends on the image resolution, model training size, and available CPU/GPU memory.
- **Overlap:** More overlap can improve detections near tile edges but increases processing time and duplicate candidates. Overlapping predictions are merged after inference.

Very large images may take considerable time on a CPU. The preview is downsampled for display, while detection reads and processes one full-resolution raster window at a time.

## Geographic area calculation

The summary always reports detection count and image coverage. Estimated weed area is also shown when the GeoTIFF has a usable coordinate reference system and affine transform metadata. The detected shapes are transformed to an equal-area coordinate system for the area calculation. If the raster has no usable spatial metadata, the app reports that geographic area is unavailable.

## Troubleshooting
 
### `NVIDIA GPU was selected, but CUDA is not available`

Select **Automatic** or **CPU**, or reinstall PyTorch using a CUDA-enabled build compatible with the device.

### 'The model does not load'

Confirm that the file is a YOLOv8-compatible `.pt` checkpoint and that its required Ultralytics version is supported by `requirements.txt`. Check `logs/weed_detection.log` for the complete error.

### 'The image does not load'

Confirm that the file is a valid GeoTIFF with at least three raster bands. The app supports `.tif` and `.tiff` file extensions.

### 'Installation fails for PyTorch, Rasterio, or another compiled package'

Use a supported 64-bit Python version, upgrade `pip`, and create a fresh virtual environment. On uncommon platforms, consult the package's installation documentation for a compatible binary build.


### If you find this repository useful, please give it a star! ⭐
