import time
import base64
from dataclasses import dataclass
from threading import Lock
from typing import Iterator

import cv2
import numpy as np
from PIL import Image

from app.config import (
    CASCADE_PATH,
    DATASET_DIR,
    FACE_SIZE,
    MAX_BRIGHTNESS,
    MIN_BRIGHTNESS,
    MIN_FACE_SIZE,
    MIN_SHARPNESS,
    RECOGNITION_THRESHOLD,
    TRAINING_DATA_PATH,
)


@dataclass
class FaceQuality:
    sharpness: float
    brightness: float
    label: str
    accepted: bool
    reason: str


@dataclass
class RecognitionResult:
    student_id: int | None
    confidence: float | None
    accepted: bool
    reason: str
    face_count: int


class FaceService:
    def __init__(self) -> None:
        self.cascade = cv2.CascadeClassifier(str(CASCADE_PATH))
        if self.cascade.empty():
            raise RuntimeError(f"Could not load Haar cascade from {CASCADE_PATH}")
        self._camera: cv2.VideoCapture | None = None
        self._camera_lock = Lock()
        self._recognizer_lock = Lock()
        self._recognizer = cv2.face.LBPHFaceRecognizer_create()
        self._model_loaded = False
        self.load_model_if_available()

    def load_model_if_available(self) -> None:
        with self._recognizer_lock:
            if TRAINING_DATA_PATH.exists():
                self._recognizer.read(str(TRAINING_DATA_PATH))
                self._model_loaded = True

    def reset_model(self) -> None:
        with self._recognizer_lock:
            self._recognizer = cv2.face.LBPHFaceRecognizer_create()
            self._model_loaded = False

    def start_camera(self) -> None:
        with self._camera_lock:
            if self._camera is not None and self._camera.isOpened():
                return
            camera = cv2.VideoCapture(0)
            if not camera.isOpened():
                raise RuntimeError("Camera could not be opened. Check macOS camera permission and close other camera apps.")
            camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self._camera = camera

    def stop_camera(self) -> None:
        with self._camera_lock:
            if self._camera is not None:
                self._camera.release()
            self._camera = None

    def read_frame(self) -> np.ndarray:
        self.start_camera()
        with self._camera_lock:
            assert self._camera is not None
            ok, frame = self._camera.read()
        if not ok or frame is None:
            raise RuntimeError("Camera frame could not be read.")
        return frame

    def detect_faces(self, gray: np.ndarray) -> list[tuple[int, int, int, int]]:
        faces = self.cascade.detectMultiScale(gray, scaleFactor=1.2, minNeighbors=6, minSize=(MIN_FACE_SIZE, MIN_FACE_SIZE))
        return sorted(faces, key=lambda face: face[2] * face[3], reverse=True)

    def frame_from_data_url(self, image_data: str) -> np.ndarray:
        if "," in image_data:
            image_data = image_data.split(",", 1)[1]
        raw = base64.b64decode(image_data)
        image_array = np.frombuffer(raw, dtype=np.uint8)
        frame = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
        if frame is None:
            raise RuntimeError("Uploaded camera frame could not be decoded.")
        return frame

    def normalize_face(self, gray: np.ndarray, face: tuple[int, int, int, int]) -> np.ndarray:
        x, y, w, h = face
        cropped = gray[y : y + h, x : x + w]
        return cv2.resize(cropped, FACE_SIZE, interpolation=cv2.INTER_AREA)

    def evaluate_face(self, normalized_face: np.ndarray) -> FaceQuality:
        sharpness = float(cv2.Laplacian(normalized_face, cv2.CV_64F).var())
        brightness = float(np.mean(normalized_face))
        if sharpness < MIN_SHARPNESS:
            return FaceQuality(sharpness, brightness, "Poor", False, "Face is blurry. Hold steady and face the camera.")
        if brightness < MIN_BRIGHTNESS:
            return FaceQuality(sharpness, brightness, "Poor", False, "Lighting is too dark.")
        if brightness > MAX_BRIGHTNESS:
            return FaceQuality(sharpness, brightness, "Poor", False, "Lighting is too bright.")
        if sharpness > 85 and MIN_BRIGHTNESS + 20 <= brightness <= MAX_BRIGHTNESS - 20:
            return FaceQuality(sharpness, brightness, "Excellent", True, "Accepted")
        return FaceQuality(sharpness, brightness, "Good", True, "Accepted")

    def stream_frames(self) -> Iterator[bytes]:
        try:
            while True:
                try:
                    frame = self.read_frame()
                except RuntimeError as exc:
                    frame = self.error_frame(str(exc))
                    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                    if ok:
                        yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                    self.stop_camera()
                    time.sleep(1)
                    continue

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.detect_faces(gray)
                for x, y, w, h in faces:
                    color = (36, 151, 255) if len(faces) == 1 else (38, 38, 255)
                    cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 82])
                if ok:
                    yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buffer.tobytes() + b"\r\n"
                time.sleep(0.04)
        finally:
            self.stop_camera()

    def error_frame(self, message: str) -> np.ndarray:
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame[:] = (23, 32, 51)
        cv2.putText(frame, "Camera unavailable", (70, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.5, (66, 185, 244), 3)
        cv2.putText(frame, message[:92], (72, 365), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (230, 236, 246), 2)
        cv2.putText(frame, "Close other camera apps and check macOS Camera permission.", (72, 420), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (230, 236, 246), 2)
        return frame

    def next_sample_index(self, student_id: int) -> int:
        indexes: list[int] = []
        for path in DATASET_DIR.glob(f"user.{student_id}.*.jpg"):
            parts = path.name.split(".")
            if len(parts) >= 4 and parts[2].isdigit():
                indexes.append(int(parts[2]))
        return max(indexes, default=0) + 1

    def capture_samples(self, student_id: int, target: int) -> dict:
        captured = 0
        skipped = 0
        reasons: list[str] = []
        sample_index = self.next_sample_index(student_id)
        saved: list[dict] = []
        max_attempts = target * 8

        for _ in range(max_attempts):
            frame = self.read_frame()
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = self.detect_faces(gray)
            if len(faces) != 1:
                skipped += 1
                reasons.append("Keep exactly one face in frame.")
                time.sleep(0.08)
                continue

            normalized = self.normalize_face(gray, faces[0])
            quality = self.evaluate_face(normalized)
            if not quality.accepted:
                skipped += 1
                reasons.append(quality.reason)
                time.sleep(0.08)
                continue

            file_path = DATASET_DIR / f"user.{student_id}.{sample_index}.jpg"
            cv2.imwrite(str(file_path), normalized)
            saved.append(
                {
                    "file_path": str(file_path),
                    "sharpness": round(quality.sharpness, 2),
                    "brightness": round(quality.brightness, 2),
                    "quality_label": quality.label,
                }
            )
            captured += 1
            sample_index += 1
            if captured >= target:
                break
            time.sleep(0.08)

        return {
            "captured": captured,
            "skipped": skipped,
            "samples": saved,
            "last_reason": reasons[-1] if reasons else "Completed",
            "success": captured >= target,
        }

    def capture_sample_from_frame(self, student_id: int, frame: np.ndarray) -> dict:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detect_faces(gray)
        if len(faces) != 1:
            return {
                "captured": 0,
                "skipped": 1,
                "samples": [],
                "last_reason": "Keep exactly one face in frame.",
                "success": False,
            }

        normalized = self.normalize_face(gray, faces[0])
        quality = self.evaluate_face(normalized)
        if not quality.accepted:
            return {
                "captured": 0,
                "skipped": 1,
                "samples": [],
                "last_reason": quality.reason,
                "success": False,
            }

        sample_index = self.next_sample_index(student_id)
        file_path = DATASET_DIR / f"user.{student_id}.{sample_index}.jpg"
        cv2.imwrite(str(file_path), normalized)
        return {
            "captured": 1,
            "skipped": 0,
            "samples": [
                {
                    "file_path": str(file_path),
                    "sharpness": round(quality.sharpness, 2),
                    "brightness": round(quality.brightness, 2),
                    "quality_label": quality.label,
                }
            ],
            "last_reason": "Accepted",
            "success": True,
        }

    def train(self) -> dict:
        faces: list[np.ndarray] = []
        ids: list[int] = []
        for image_path in sorted(DATASET_DIR.glob("user.*.*.jpg")):
            parts = image_path.name.split(".")
            if len(parts) < 4 or not parts[1].isdigit():
                continue
            face_image = Image.open(image_path).convert("L")
            face_array = np.array(face_image, dtype=np.uint8)
            if face_array.shape != FACE_SIZE:
                face_array = cv2.resize(face_array, FACE_SIZE, interpolation=cv2.INTER_AREA)
            faces.append(face_array)
            ids.append(int(parts[1]))

        if not faces:
            raise RuntimeError("No face samples found. Register at least one student first.")

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(faces, np.array(ids, dtype=np.int32))
        recognizer.save(str(TRAINING_DATA_PATH))
        with self._recognizer_lock:
            self._recognizer = recognizer
            self._model_loaded = True

        return {
            "model_path": str(TRAINING_DATA_PATH),
            "student_count": len(set(ids)),
            "sample_count": len(faces),
        }

    def recognize_current_face(self) -> RecognitionResult:
        if not self._model_loaded:
            self.load_model_if_available()
        if not self._model_loaded:
            return RecognitionResult(None, None, False, "Model is not trained yet.", 0)

        frame = self.read_frame()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detect_faces(gray)
        if len(faces) == 0:
            return RecognitionResult(None, None, False, "No face detected.", 0)
        if len(faces) > 1:
            return RecognitionResult(None, None, False, "Multiple faces detected. Attendance needs one face at a time.", len(faces))

        normalized = self.normalize_face(gray, faces[0])
        quality = self.evaluate_face(normalized)
        if not quality.accepted:
            return RecognitionResult(None, None, False, quality.reason, 1)

        with self._recognizer_lock:
            student_id, confidence = self._recognizer.predict(normalized)

        confidence_value = float(confidence)
        if confidence_value > RECOGNITION_THRESHOLD:
            return RecognitionResult(None, confidence_value, False, "Face not confidently matched.", 1)
        return RecognitionResult(int(student_id), confidence_value, True, "Recognized", 1)

    def recognize_frame(self, frame: np.ndarray) -> RecognitionResult:
        if not self._model_loaded:
            self.load_model_if_available()
        if not self._model_loaded:
            return RecognitionResult(None, None, False, "Model is not trained yet.", 0)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.detect_faces(gray)
        if len(faces) == 0:
            return RecognitionResult(None, None, False, "No face detected.", 0)
        if len(faces) > 1:
            return RecognitionResult(None, None, False, "Multiple faces detected. Attendance needs one face at a time.", len(faces))

        normalized = self.normalize_face(gray, faces[0])
        quality = self.evaluate_face(normalized)
        if not quality.accepted:
            return RecognitionResult(None, None, False, quality.reason, 1)

        with self._recognizer_lock:
            student_id, confidence = self._recognizer.predict(normalized)

        confidence_value = float(confidence)
        if confidence_value > RECOGNITION_THRESHOLD:
            return RecognitionResult(None, confidence_value, False, "Face not confidently matched.", 1)
        return RecognitionResult(int(student_id), confidence_value, True, "Recognized", 1)


face_service = FaceService()
