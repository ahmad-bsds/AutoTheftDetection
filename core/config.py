class Settings:
    def __init__(self):
        self.UPLOAD_DIR = "data/uploads"
        self.MODEL_PATH = "models/yolov8n.pt"
        self.PLATE_MODEL = "models/license_plate_detector.pt"
        self.STOLEN_PLATES_CSV = "data/stolen_vehicles.csv"

settings = Settings()
