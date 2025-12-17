import cv2
import mediapipe as mp
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
import mediapipe.python.solutions.face_mesh as mp_face_mesh

class EyeTrackerThread(QThread):
    blink_detected = pyqtSignal(int)

    def __init__(self):
        super().__init__()
        self.running = True
        self.blink_count = 0
        # MediaPipe Landmark Indices
        self.LEFT_EYE = [33, 160, 158, 133, 153, 144]
        self.RIGHT_EYE = [362, 385, 387, 263, 373, 380]
        self.EAR_THRESH = 0.21
        self.CONSEC_FRAMES = 2

    def euclidean_dist(self, pt1, pt2):
        return np.linalg.norm(np.array(pt1) - np.array(pt2))

    def eye_aspect_ratio(self, eye_landmarks):
        A = self.euclidean_dist(eye_landmarks[1], eye_landmarks[5])
        B = self.euclidean_dist(eye_landmarks[2], eye_landmarks[4])
        C = self.euclidean_dist(eye_landmarks[0], eye_landmarks[3])
        return (A + B) / (2.0 * C)

    def run(self):
        cap = cv2.VideoCapture(0)
        frame_counter = 0
        # mp_face_mesh = mp.solutions.face_mesh
        # mp_face_mesh = mp.solutions.face_mesh
        with mp_face_mesh.FaceMesh(
            max_num_faces=1, refine_landmarks=True,
            min_detection_confidence=0.5, min_tracking_confidence=0.5
        ) as face_mesh:
            while self.running:
                ret, frame = cap.read()
                if not ret: break

                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                results = face_mesh.process(rgb)

                if results.multi_face_landmarks: #type:ignore
                    h, w, _ = frame.shape
                    face_landmarks = results.multi_face_landmarks[0] #type:ignore
                    
                    l_eye = [(int(face_landmarks.landmark[i].x * w), int(face_landmarks.landmark[i].y * h)) for i in self.LEFT_EYE]
                    r_eye = [(int(face_landmarks.landmark[i].x * w), int(face_landmarks.landmark[i].y * h)) for i in self.RIGHT_EYE]
                    
                    ear = (self.eye_aspect_ratio(l_eye) + self.eye_aspect_ratio(r_eye)) / 2.0

                    if ear < self.EAR_THRESH:
                        frame_counter += 1
                    else:
                        if frame_counter >= self.CONSEC_FRAMES:
                            self.blink_count += 1
                            self.blink_detected.emit(self.blink_count)
                        frame_counter = 0

        cap.release()

    def stop(self):
        self.running = False
        self.wait()