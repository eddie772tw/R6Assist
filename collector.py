# Copyright (C) 2026 R6Assist Developers
import os
import cv2
import time
import datetime

class DataCollector:
    def __init__(self, base_dir=None):
        if base_dir is None:
            # Default to project_root/dataset/collected_data
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(current_file)
            self.base_dir = os.path.join(project_root, "dataset", "collected_data")
        else:
            self.base_dir = base_dir

        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
            print(f"Created collection directory: {self.base_dir}")

    def save_sample(self, image, label, confidence):
        """
        Save a single image sample to the appropriate directory.

        Args:
            image (numpy.ndarray): The cropped image (BGR format).
            label (str): The recognized class name (e.g., "Ash", "Unknown").
            confidence (float): The recognition confidence.
        """
        if image is None or image.size == 0:
            return

        # Sanitize label just in case
        safe_label = "".join([c for c in label if c.isalnum() or c in (' ', '_', '-')]).strip()
        if not safe_label:
            safe_label = "Unknown"

        # Create target directory
        target_dir = os.path.join(self.base_dir, safe_label)
        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)

        # Generate filename: timestamp_confidence.jpg
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        filename = f"{timestamp}_{confidence:.2f}.jpg"
        filepath = os.path.join(target_dir, filename)

        try:
            # cv2.imwrite does not support non-ASCII paths on Windows.
            # Use imencode + binary write instead.
            is_success, buffer = cv2.imencode(".jpg", image)
            if is_success:
                with open(filepath, "wb") as f:
                    f.write(buffer)
            else:
                print(f"Failed to encode image for {label}")
        except Exception as e:
            print(f"Failed to save sample for {label}: {e}")

    def process_batch(self, images, labels, confidences):
        """
        Process a batch of results from the analyzer.
        """
        if len(images) != len(labels) or len(images) != len(confidences):
            print("Error: Batch size mismatch in DataCollector")
            return

        for img, lbl, conf in zip(images, labels, confidences):
            self.save_sample(img, lbl, conf)
