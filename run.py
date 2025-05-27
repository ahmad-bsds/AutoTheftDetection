from fastapi.middleware.wsgi import WSGIMiddleware
from api.main import fast_app
from app.flask_ui import app
import uvicorn
from werkzeug.middleware.dispatcher import DispatcherMiddleware


# Mount Flask UI under FastAPI
fast_app.mount("/", WSGIMiddleware(app))

if __name__ == "__main__":
    print("🚀 Starting Auto Theft Detection App at http://127.0.0.1:8000 ...")
    uvicorn.run("run:fast_app", host="127.0.0.1", port=8000, reload=True)