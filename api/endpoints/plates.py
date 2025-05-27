import os
import cv2
import time
from threading import Lock
from pydantic import BaseModel
from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
import pandas as pd
from prediction.main import AutoTheftDetector
from werkzeug.utils import secure_filename
from core.config import settings
from core.logger import get_logger
router = APIRouter()

logger = get_logger(__name__)

CSV_FILE = settings.STOLEN_PLATES_CSV
# os.remove(CSV_FILE)

# Global State
detector = AutoTheftDetector()
video_source = None
is_theft_status = {"value": False}
is_theft_lock = Lock()

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "Auto Theft Detection API is online"}


@router.post("/upload_video")
async def upload_video(video: UploadFile = File(...)):
    """
    Upload a video file to run auto-theft detection.
    """
    global video_source, detector

    filename = secure_filename(video.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)

    with open(save_path, "wb") as f:
        f.write(await video.read())

    detector = AutoTheftDetector()  # reset session
    video_source = save_path

    return {"message": f"Video uploaded and saved as {filename}"}


@router.post("/set_stream_url")
async def set_stream_url(url: str = Query(..., description="Stream URL (e.g., RTSP or HTTP MJPEG)")):
    """
    Set a video stream URL as input source.
    """
    global video_source, detector

    if not detector.is_valid_stream(url):
        raise HTTPException(status_code=400, detail="Invalid or inaccessible video stream URL")

    detector = AutoTheftDetector()  # reset session
    video_source = url

    return {"message": "Stream URL accepted and processing started", "source": url}


@router.get("/video_feed")
async def video_feed():
    """
    Start MJPEG stream from either uploaded video or live URL.
    """
    if not video_source:
        raise HTTPException(status_code=400, detail="No video source set (upload a file or set stream URL)")

    return StreamingResponse(
        generate_mjpeg_stream(video_source),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@router.get("/stolen_plates")
async def get_stolen_plates():
    """
    Get list of detected stolen license plates.
    """
    return {"stolen_plates": detector.get_detected_stolen_plates()}


@router.get("/is_theft")
async def get_theft_status():
    """
    Return current theft detection status (True/False).
    """
    with is_theft_lock:
        return {"is_theft": is_theft_status["value"]}

class PlateSchema(BaseModel):
    plate: str

@router.post("/app/plates/add")
def add_plate(plate: PlateSchema):
    plate_number = plate.plate.upper()

    # Ensure the CSV exists
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=["plate"])
        df.to_csv(CSV_FILE, index=False)

    df = pd.read_csv(CSV_FILE)
    
    if plate_number in df["plate"].values:
        raise HTTPException(status_code=400, detail="Plate already exists")
    
    try:
        # Add plate using loc
        df.loc[len(df)] = plate_number
        df.to_csv(CSV_FILE, index=False)
        logger.info(f"Number plate {plate_number} added successfully!")
        return {"message": f"Plate {plate_number} added"}
    
    except Exception as e:
        logger.error(f"Error adding plate: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


    
    
@router.post("/app/plates/delete")
def del_plate(plate: PlateSchema):
    plate_number = plate.plate.upper()
    
    # Ensure CSV file exists
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=["plate"])
        df.to_csv(CSV_FILE, index=False)

    df = pd.read_csv(CSV_FILE)
    
    if plate_number not in df["plate"].values:
        raise HTTPException(status_code=400, detail="Plate does not exist.")
    
    try:
        # Delete plate entry
        df = df[df["plate"] != plate_number]
        df.to_csv(CSV_FILE, index=False)
        logger.info(f"Number plate {plate_number} deleted successfully!")
        return {"message": f"Plate {plate_number} deleted"}
    except Exception as e:
        logger.error(f"Error deleting plate: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")




def generate_mjpeg_stream(source):
    """
    Generator function to stream frames over HTTP with MJPEG.
    """
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise HTTPException(status_code=500, detail="Failed to open video source")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame, is_theft = detector.process_frame(frame)

        frame = cv2.resize(frame, (640, 480))

        # Update global theft flag
        with is_theft_lock:
            is_theft_status["value"] = is_theft

        _, buffer = cv2.imencode(".jpg", frame)
        frame_bytes = buffer.tobytes()

        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n")

    cap.release()


