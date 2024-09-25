from collections import defaultdict
import cv2, os
import numpy as np
from ultralytics import YOLO
from shapely.geometry import *
from statistics import mode
import datetime
from uuid import UUID
import torch
from pathlib import Path


def line_direction(p1, p2, p3, p4):
    A = [p2[0] - p1[0], p2[1] - p1[1]]
    B = [p4[0] - p3[0], p4[1] - p3[1]]

    # 2D cross product for forward/backward check
    cross_product = A[0] * B[1] - A[1] * B[0]

    if cross_product < 0:
        return "Forward"
    elif cross_product > 0:
        return "Backward"
    else:
        return "Indeterminate direction"


class Detection:
    def __init__(self, device, viz_mode) -> None:
        self.track_history = defaultdict(
            lambda: {"track": [], "name": [], "counted": False}
        )
        self.device = torch.device(device)
        self.viz_mode = viz_mode

    def setVizMode(self, mode:int):
        self.viz_mode = mode

    def selectDevice(self, device_name: str):
        self.device = torch.device(device_name)

    def loadModel(self, model_path:str):
        # check for model path
        if not os.path.exists(model_path):
            raise Exception("Invalid model path provided")
        # load model
        model = YOLO(model_path)
        # If the model loading fails, raise an error
        if model is None:
            raise Exception("unable to load model")

        self.model_path = model_path
        self.model = model
        self.model.to(self.device)

    def resetModel(self):
        self.track_history = defaultdict(lambda: {"track": [], "name": [], "counted": False})
        self.loadModel(self.model_path)

    def detectAndTracePath(
        self, frame: np.ndarray, lines: list[dict], frame_time: str, callback: callable
    ) -> np.ndarray:
        

        if self.model is None:
            return frame

        # Run YOLOv8 tracking on the frame, persisting tracks between frames
        results = self.model.track(frame, persist=True, verbose=False)
        try:
            track_ids = results[0].boxes.id.int().cpu().tolist()
        except:
            track_ids = []

        track_history_to_delete = set(self.track_history.keys()) - set(track_ids)

        for id in track_history_to_delete:
            del self.track_history[id]

        # Visualize the results on the frame
        frame = results[0].plot(
            line_width=2, font_size=2, probs=False ,
            boxes= (self.viz_mode in [0 , 2])
        )

        # draw cross line
        for line_id, l in lines.items():
            line_geom = LineString(l["geometry"])
            # pts = np.array(l["geometry"], dtype=np.int32).reshape((-1, 1, 2))
            # cv2.polylines(frame, pts=[pts], isClosed=False, color=l["color"], thickness=2)

            for item in results[0].summary():
                bbox_id = item.get("track_id")
                if bbox_id is None:
                    continue

                class_label = item.get("name")
                x1, y1, x2, y2 = item.get("box").values()
                track = self.track_history[bbox_id]

                track["name"].append(class_label)
                track["track"].append(((x1 + x2) / 2, (y1 + y2) / 2))
                if len(track["track"]) > 20:
                    track["track"].pop(0)
                    track["name"].pop(0)

                if len(track["track"]) > 1 and not track["counted"]:
                    track_geom = LineString(track["track"])
                    is_intersects = line_geom.intersects(track_geom)
                    if is_intersects:
                        direction = line_direction(
                            l["geometry"][0],
                            l["geometry"][-1],
                            track["track"][0],
                            track["track"][-1],
                        )
                        vechile = mode(track["name"])
                        track["counted"] = True
                        callback(
                            {
                                "line_id": line_id,
                                "track_id": bbox_id,
                                "crossing_time": frame_time,
                                "vechile": vechile,
                                "direction": direction,
                            }
                        )
                
                if self.viz_mode in [1, 2]:
                    points = np.hstack(track["track"]).astype(np.int32).reshape((-1, 1, 2))
                    cv2.polylines(
                        frame,
                        [points],
                        isClosed=False,
                        color=(0, 250, 250),
                        thickness=2,
                        lineType=cv2.LINE_AA,
                    )

        return frame


if __name__ == "__main__":

    # print(list_devices())

    lines = {}
    # Open the video file
    video_path = r"C:\Users\KoushikKarmakar\Desktop\yolo object detection\media_files\SAMPLE VIDEO\Test Video.mp4"

    cap = cv2.VideoCapture(video_path)

    detection = Detection()
    print(123)
    detection.loadModel(
        r"C:\Users\KoushikKarmakar\Desktop\yolo object detection\gui\trained_models\yolov8n.pt"
    )
    start_time = datetime.datetime.now()
    # Loop through the video frames
    while cap.isOpened():
        # Read a frame from the video
        success, frame = cap.read()

        if success:
            # detect and track
            frame = detection.detectAndTracePath(frame, lines, '123',print)
            # Display the annotated frame
            cv2.imshow("YOLOv8 Tracking", frame)
            # Break the loop if 'q' is pressed
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break
        else:
            # Break the loop if the end of the video is reached
            break

    # Release the video capture object and close the display window
    cap.release()
    cv2.destroyAllWindows()
