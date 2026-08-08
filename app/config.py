from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = ROOT_DIR / "database.db"
DATASET_DIR = ROOT_DIR / "dataset"
RECOGNIZER_DIR = ROOT_DIR / "recognizer"
EXPORT_DIR = ROOT_DIR / "exports"
CASCADE_PATH = ROOT_DIR / "haarcascade_frontalface_default.xml"
TRAINING_DATA_PATH = RECOGNIZER_DIR / "trainingdata.yml"

FACE_SIZE = (220, 220)
DEFAULT_SAMPLE_TARGET = 35
MIN_FACE_SIZE = 90
MIN_SHARPNESS = 35.0
MIN_BRIGHTNESS = 45.0
MAX_BRIGHTNESS = 215.0
RECOGNITION_THRESHOLD = 72.0


for folder in (DATASET_DIR, RECOGNIZER_DIR, EXPORT_DIR):
    folder.mkdir(parents=True, exist_ok=True)
