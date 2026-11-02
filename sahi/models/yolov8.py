# OBSS SAHI Tool
# Code written by AnNT, 2023.

import ast
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
import torch

logger = logging.getLogger(__name__)

from sahi.models.base import DetectionModel
from sahi.prediction import ObjectPrediction
from sahi.utils.compatibility import fix_full_shape_list, fix_shift_amount_list
from sahi.utils.cv import get_coco_segmentation_from_bool_mask
from sahi.utils.import_utils import check_requirements


class Yolov8DetectionModel(DetectionModel):
    SUPPORTED_MODEL_FORMATS = {".pt", ".onnx", ".engine"}

    def check_dependencies(self) -> None:
        check_requirements(["ultralytics"])

    @staticmethod
    def _normalise_image_size(value):
        if isinstance(value, int):
            return value
        if isinstance(value, (list, tuple)) and len(value) >= 2:
            height, width = int(value[-2]), int(value[-1])
            return height if height == width else [height, width]
        return None

    @staticmethod
    def _normalise_names(value):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                value = ast.literal_eval(value)
        if isinstance(value, dict):
            return {str(index): name for index, name in value.items()}
        return None

    @classmethod
    def _read_export_info(cls, model_path):
        """Return task and static input size embedded in an exported model."""
        path = Path(model_path)
        if path.suffix.lower() == ".engine":
            with path.open("rb") as engine_file:
                metadata_length = int.from_bytes(
                    engine_file.read(4), byteorder="little", signed=True
                )
                if metadata_length <= 0 or metadata_length > 1_000_000:
                    raise ValueError("TensorRT engine has invalid Ultralytics metadata")
                metadata = json.loads(engine_file.read(metadata_length).decode("utf-8"))
            return (
                metadata.get("task"),
                cls._normalise_image_size(metadata.get("imgsz")),
                cls._normalise_names(metadata.get("names")),
            )

        if path.suffix.lower() == ".onnx":
            import onnx

            graph = onnx.load(str(path), load_external_data=False)
            metadata = {item.key: item.value for item in graph.metadata_props}
            dimensions = graph.graph.input[0].type.tensor_type.shape.dim
            static_shape = [dimension.dim_value for dimension in dimensions[-2:]]
            image_size = None
            if len(static_shape) == 2 and all(static_shape):
                image_size = cls._normalise_image_size(static_shape)
            return (
                metadata.get("task"),
                image_size,
                cls._normalise_names(metadata.get("names")),
            )

        return None, None, None

    def load_model(self):
        """
        Detection model is initialized and set to self.model.
        """

        from ultralytics import YOLO

        try:
            suffix = Path(self.model_path).suffix.lower()
            if suffix not in self.SUPPORTED_MODEL_FORMATS:
                supported = ", ".join(sorted(self.SUPPORTED_MODEL_FORMATS))
                raise ValueError(f"supported model formats are: {supported}")

            task, exported_image_size, exported_names = self._read_export_info(self.model_path)
            model = YOLO(self.model_path, task=task)
            if suffix == ".pt":
                model.to(self.device)
                if self.image_size is None:
                    self.image_size = self._normalise_image_size(model.overrides.get("imgsz"))
            elif exported_image_size is not None:
                self.image_size = exported_image_size
            if not self.category_mapping and exported_names:
                self.category_mapping = exported_names
            self.set_model(model)
        except Exception as e:
            raise TypeError(f"model_path is not a valid Ultralytics YOLO model: {e}") from e

    def set_model(self, model: Any):
        """
        Sets the underlying YOLOv8 model.
        Args:
            model: Any
                A YOLOv8 model
        """

        self.model = model
        self.last_inference_seconds = 0.0
        # set category_mapping
        if not self.category_mapping:
            names = self.model.names
            self.category_mapping = {
                str(index): name for index, name in names.items()
            }

    def _prediction_kwargs(self):
        kwargs = {
            "verbose": False,
            "conf": self.confidence_threshold,
            "device": self.device,
        }
        if self.config_path is not None:
            kwargs["cfg"] = self.config_path
        if self.image_size is not None:
            kwargs["imgsz"] = self.image_size
        return kwargs

    def warmup(self):
        """Load and warm a TensorRT engine before timed detection begins."""
        if Path(self.model_path).suffix.lower() != ".engine":
            return
        if isinstance(self.image_size, int):
            height = width = self.image_size
        elif isinstance(self.image_size, (list, tuple)) and len(self.image_size) >= 2:
            height, width = self.image_size[-2:]
        else:
            raise ValueError("TensorRT engine input dimensions are unavailable")
        image = np.zeros((int(height), int(width), 3), dtype=np.uint8)
        self.model(image, **self._prediction_kwargs())

    def perform_inference(self, image: np.ndarray):
        """
        Prediction is performed using self.model and the prediction result is set to self._original_predictions.
        If predictions have masks, each prediction is a tuple like (boxes, masks).
        Args:
            image: np.ndarray
                A numpy array that contains the image to be predicted. 3 channel image should be in RGB order.

        """

        # Confirm model is loaded
        if self.model is None:
            raise ValueError("Model is not loaded, load it by calling .load_model()")

        prediction_result = self.model(
            image[:, :, ::-1], **self._prediction_kwargs()
        )  # YOLOv8 expects numpy arrays to have BGR
        self.last_inference_seconds = sum(
            result.speed.get("inference", 0.0) for result in prediction_result
        ) / 1000.0

        if self.has_mask:
            # We do not filter results again as confidence threshold is already applied above
            prediction_result = [
                (
                    result.boxes.data,
                    result.masks.data
                    if result.masks is not None
                    else torch.empty(
                        (0, *result.boxes.orig_shape),
                        device=result.boxes.data.device,
                    ),
                )
                for result in prediction_result
            ]

        else:  # If model doesn't do segmentation then no need to check masks
            # We do not filter results again as confidence threshold is already applied above
            prediction_result = [result.boxes.data for result in prediction_result]

        self._original_predictions = prediction_result
        self._original_shape = image.shape

    @property
    def category_names(self):
        return self.category_mapping.values()

    @property
    def num_categories(self):
        """
        Returns number of categories
        """
        return len(self.model.names)

    @property
    def has_mask(self):
        """
        Returns if model output contains segmentation mask
        """
        return self.model.task == "segment"

    def _create_object_prediction_list_from_original_predictions(
        self,
        shift_amount_list: Optional[List[List[int]]] = [[0, 0]],
        full_shape_list: Optional[List[List[int]]] = None,
    ):
        """
        self._original_predictions is converted to a list of prediction.ObjectPrediction and set to
        self._object_prediction_list_per_image.
        Args:
            shift_amount_list: list of list
                To shift the box and mask predictions from sliced image to full sized image, should
                be in the form of List[[shift_x, shift_y],[shift_x, shift_y],...]
            full_shape_list: list of list
                Size of the full image after shifting, should be in the form of
                List[[height, width],[height, width],...]
        """
        original_predictions = self._original_predictions

        # compatilibty for sahi v0.8.15
        shift_amount_list = fix_shift_amount_list(shift_amount_list)
        full_shape_list = fix_full_shape_list(full_shape_list)
        # handle all predictions
        object_prediction_list_per_image = []
        for image_ind, image_predictions in enumerate(original_predictions):
            shift_amount = shift_amount_list[image_ind]
            full_shape = None if full_shape_list is None else full_shape_list[image_ind]
            object_prediction_list = []
            if self.has_mask:
                image_predictions_in_xyxy_format = image_predictions[0]
                image_predictions_masks = image_predictions[1]
                for prediction, bool_mask in zip(
                    image_predictions_in_xyxy_format.cpu().detach().numpy(),
                    image_predictions_masks.cpu().detach().numpy(),
                ):
                    x1 = prediction[0]
                    y1 = prediction[1]
                    x2 = prediction[2]
                    y2 = prediction[3]
                    bbox = [x1, y1, x2, y2]
                    score = prediction[4]
                    category_id = int(prediction[5])
                    category_name = self.category_mapping[str(category_id)]

                    orig_width = self._original_shape[1]
                    orig_height = self._original_shape[0]
                    bool_mask = cv2.resize(bool_mask.astype(np.uint8), (orig_width, orig_height))
                    segmentation = get_coco_segmentation_from_bool_mask(bool_mask)
                    if len(segmentation) == 0:
                        continue
                    # fix negative box coords
                    bbox[0] = max(0, bbox[0])
                    bbox[1] = max(0, bbox[1])
                    bbox[2] = max(0, bbox[2])
                    bbox[3] = max(0, bbox[3])

                    # fix out of image box coords
                    if full_shape is not None:
                        bbox[0] = min(full_shape[1], bbox[0])
                        bbox[1] = min(full_shape[0], bbox[1])
                        bbox[2] = min(full_shape[1], bbox[2])
                        bbox[3] = min(full_shape[0], bbox[3])

                    # ignore invalid predictions
                    if not (bbox[0] < bbox[2]) or not (bbox[1] < bbox[3]):
                        logger.warning(f"ignoring invalid prediction with bbox: {bbox}")
                        continue
                    object_prediction = ObjectPrediction(
                        bbox=bbox,
                        category_id=category_id,
                        score=score,
                        segmentation=segmentation,
                        category_name=category_name,
                        shift_amount=shift_amount,
                        full_shape=full_shape,
                    )
                    object_prediction_list.append(object_prediction)
                object_prediction_list_per_image.append(object_prediction_list)
            else:  # Only bounding boxes
                # process predictions
                for prediction in image_predictions.data.cpu().detach().numpy():
                    x1 = prediction[0]
                    y1 = prediction[1]
                    x2 = prediction[2]
                    y2 = prediction[3]
                    bbox = [x1, y1, x2, y2]
                    score = prediction[4]
                    category_id = int(prediction[5])
                    category_name = self.category_mapping[str(category_id)]

                    # fix negative box coords
                    bbox[0] = max(0, bbox[0])
                    bbox[1] = max(0, bbox[1])
                    bbox[2] = max(0, bbox[2])
                    bbox[3] = max(0, bbox[3])

                    # fix out of image box coords
                    if full_shape is not None:
                        bbox[0] = min(full_shape[1], bbox[0])
                        bbox[1] = min(full_shape[0], bbox[1])
                        bbox[2] = min(full_shape[1], bbox[2])
                        bbox[3] = min(full_shape[0], bbox[3])

                    # ignore invalid predictions
                    if not (bbox[0] < bbox[2]) or not (bbox[1] < bbox[3]):
                        logger.warning(f"ignoring invalid prediction with bbox: {bbox}")
                        continue

                    object_prediction = ObjectPrediction(
                        bbox=bbox,
                        category_id=category_id,
                        score=score,
                        segmentation=None,
                        category_name=category_name,
                        shift_amount=shift_amount,
                        full_shape=full_shape,
                    )
                    object_prediction_list.append(object_prediction)
                object_prediction_list_per_image.append(object_prediction_list)

        self._object_prediction_list_per_image = object_prediction_list_per_image
