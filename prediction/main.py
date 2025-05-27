import os
import cv2
import numpy as np
import pandas as pd
from datetime import datetime
from ultralytics import YOLO
from sort.sort import Sort
from core.config import settings
from core.logger import get_logger
from util import get_car, read_license_plate


class AutoTheftDetector:
    def __init__(self):
        self.logger = get_logger(__name__)
        self.vehicle_model = YOLO(settings.MODEL_PATH)
        self.plate_model = YOLO(settings.PLATE_MODEL)
        self.tracker = Sort()
        self.vehicle_classes = [2, 3, 5, 7]  # Car, Motorcycle, Bus, Truck
        self.stolen_plates = self._load_stolen_plates()
        self.detected_stolen = set()
        self.all_seen_plates = {}
        self.stolen_log = []
        self.is_theft_detected = False

    def _load_stolen_plates(self):
        try:
            df = pd.read_csv(settings.STOLEN_PLATES_CSV)
            return set(df['plate'].str.strip().str.upper().tolist())
        except Exception as e:
            self.logger.error(f"Failed to load stolen plates: {e}")
            return set()

    def _log_theft(self, plate_num, frame):
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        filename = f"{plate_num}_{timestamp}.jpg"
        save_path = os.path.join("static", "thefted", filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        cv2.imwrite(save_path, frame)

        self.stolen_log.append({
            "plate": plate_num,
            "image": save_path,
            "timestamp": timestamp
        })

    def process_frame(self, frame):
        detections = self.vehicle_model(frame)[0]
        vehicle_detections = [
            [x1, y1, x2, y2, score]
            for x1, y1, x2, y2, score, class_id in detections.boxes.data.tolist()
            if int(class_id) in self.vehicle_classes
        ]
        tracked = self.tracker.update(np.array(vehicle_detections))

        plates = self.plate_model(frame)[0]
        for plate in plates.boxes.data.tolist():
            lx1, ly1, lx2, ly2, score, class_id = plate
            xcar1, ycar1, xcar2, ycar2, car_id = get_car(plate, tracked)
            if car_id == -1:
                continue

            lp_crop = frame[int(ly1):int(ly2), int(lx1):int(lx2)]
            if lp_crop.size == 0:
                continue

            gray = cv2.cvtColor(lp_crop, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 64, 255, cv2.THRESH_BINARY_INV)
            text, _ = read_license_plate(thresh)

            if text:
                plate_num = text.strip().upper()
                self.all_seen_plates[car_id] = plate_num
                is_stolen = plate_num in self.stolen_plates

                color = (0, 0, 255) if is_stolen else (0, 255, 0)

                if is_stolen:
                    if plate_num not in self.detected_stolen:
                        self.logger.critical(f"🚨 STOLEN VEHICLE DETECTED: {plate_num}")
                        self.detected_stolen.add(plate_num)
                        self._log_theft(plate_num, frame)
                    self.is_theft_detected = True
                else:
                    self.logger.info(f"Vehicle Detected: {plate_num}")
                    self.is_theft_detected = False

                # Draw car bounding box (bold)
                cv2.rectangle(frame, (int(xcar1), int(ycar1)), (int(xcar2), int(ycar2)), color, 4)

                # Draw license plate bounding box (bold, blueish)
                cv2.rectangle(frame, (int(lx1), int(ly1)), (int(lx2), int(ly2)), (255, 0, 0), 3)

                # Draw license plate text near plate box (large, thick font)
                cv2.putText(frame, plate_num, (int(lx1), int(ly1) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 255), 3)

        return frame, self.is_theft_detected


    def process_video(self, source):
        """
        Process video from file path or video stream URL.
        :param source: Path to video file or stream URL (e.g., RTSP, HTTP MJPEG)
        """
        cap = cv2.VideoCapture(source)

        if not cap.isOpened():
            self.logger.error(f"❌ Unable to open video source: {source}")
            return

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            processed_frame, _ = self.process_frame(frame)

            # Optional live display (debug or local use)
            cv2.imshow("Auto Theft Detection", processed_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

    def get_detected_stolen_plates(self):
        """
        Returns a list of dicts: { 'plate', 'image', 'timestamp' }
        """
        return self.stolen_log

    def is_valid_stream(self, url):
        cap = cv2.VideoCapture(url)
        if cap.isOpened():
            cap.release()
            return True
        return False
