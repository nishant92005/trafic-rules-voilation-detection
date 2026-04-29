from __future__ import annotations

import math
import os
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import cv2
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent
ULTRALYTICS_DIR = PROJECT_DIR / ".ultralytics"
ULTRALYTICS_DIR.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(ULTRALYTICS_DIR))

from email_alert import send_violation_alert


COCO_MODEL = None
PERSON_CLASS_ID = 0
MOTORCYCLE_CLASS_ID = 3


def _env_int(name: str, default: int, minimum: int = 1) -> int:
    try:
        return max(minimum, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def _env_float(name: str, default: float, minimum: float = 0.0) -> float:
    try:
        return max(minimum, float(os.getenv(name, str(default))))
    except ValueError:
        return default


def _get_model():
    global COCO_MODEL
    if COCO_MODEL is None:
        from ultralytics import YOLO

        COCO_MODEL = YOLO("yolov8n.pt")
    return COCO_MODEL


def _box_center(box: List[float]) -> Tuple[float, float]:
    x1, y1, x2, y2 = box
    return (x1 + x2) / 2, (y1 + y2) / 2


def _box_bottom_center(box: List[float]) -> Tuple[float, float]:
    x1, _, x2, y2 = box
    return (x1 + x2) / 2, y2


def _box_area(box: List[float]) -> float:
    x1, y1, x2, y2 = box
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _intersection_area(box_a: List[float], box_b: List[float]) -> float:
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b
    x1 = max(ax1, bx1)
    y1 = max(ay1, by1)
    x2 = min(ax2, bx2)
    y2 = min(ay2, by2)
    return max(0.0, x2 - x1) * max(0.0, y2 - y1)


def _inside_region(point: Tuple[float, float], region: List[float]) -> bool:
    px, py = point
    x1, y1, x2, y2 = region
    return x1 <= px <= x2 and y1 <= py <= y2


def _approximate_helmet(frame: np.ndarray, person_box: List[float]) -> bool:
    x1, y1, x2, y2 = map(int, person_box)
    height = max(1, y2 - y1)
    width = max(1, x2 - x1)

    head_y2 = y1 + max(20, int(height * 0.24))
    head_x1 = x1 + int(width * 0.2)
    head_x2 = x2 - int(width * 0.2)
    head_roi = frame[max(0, y1):max(0, head_y2), max(0, head_x1):max(0, head_x2)]

    if head_roi.size == 0:
        return False

    gray = cv2.cvtColor(head_roi, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    edges = cv2.Canny(blurred, 70, 150)
    edge_density = float(np.count_nonzero(edges)) / edges.size

    circles = cv2.HoughCircles(
        blurred,
        cv2.HOUGH_GRADIENT,
        dp=1.2,
        minDist=max(8, head_roi.shape[1] // 3),
        param1=90,
        param2=18,
        minRadius=max(6, min(head_roi.shape[:2]) // 8),
        maxRadius=max(12, min(head_roi.shape[:2]) // 2),
    )

    hsv = cv2.cvtColor(head_roi, cv2.COLOR_BGR2HSV)
    saturation = float(np.mean(hsv[:, :, 1])) / 255.0
    brightness_std = float(np.std(gray)) / 255.0

    has_circle = circles is not None and len(circles[0]) > 0
    strong_surface = saturation > 0.23 and brightness_std < 0.24
    return has_circle or (strong_surface and 0.08 < edge_density < 0.22)


def _score_person_for_bike(person_box: List[float], bike_box: List[float]) -> float:
    px1, py1, px2, py2 = person_box
    bx1, by1, bx2, by2 = bike_box

    expanded = [bx1 - 50, by1 - 70, bx2 + 50, by2 + 110]
    foot_point = _box_bottom_center(person_box)
    center_point = _box_center(person_box)

    if not (_inside_region(foot_point, expanded) or _inside_region(center_point, expanded)):
        return -1.0

    overlap_ratio = _intersection_area(person_box, expanded) / max(_box_area(person_box), 1.0)
    bike_center = _box_center(bike_box)
    foot_distance = math.dist(foot_point, bike_center)
    normalized_distance = foot_distance / max(40.0, (bx2 - bx1) + (by2 - by1))

    return overlap_ratio + max(0.0, 1.0 - normalized_distance)


def _associate_people_to_bikes(
    people: List[Dict[str, List[float]]],
    motorcycles: List[Dict[str, List[float]]],
) -> List[Dict[str, object]]:
    groups = [{"motorcycle": bike, "riders": []} for bike in motorcycles]

    for person in people:
        best_index = None
        best_score = 0.0

        for idx, bike in enumerate(motorcycles):
            score = _score_person_for_bike(person["box"], bike["box"])
            if score > best_score:
                best_score = score
                best_index = idx

        if best_index is not None:
            groups[best_index]["riders"].append(person)

    return groups


def _run_detection(
    model,
    frame: np.ndarray,
    inference_width: int,
    confidence_threshold: float,
) -> Tuple[List[Dict[str, object]], List[Dict[str, List[float]]], List[Dict[str, object]]]:
    height, width = frame.shape[:2]
    scale = 1.0
    infer_frame = frame

    if inference_width > 0 and width > inference_width:
        scale = inference_width / width
        infer_height = max(1, int(height * scale))
        infer_frame = cv2.resize(frame, (inference_width, infer_height), interpolation=cv2.INTER_AREA)

    results = model(
        infer_frame,
        verbose=False,
        imgsz=inference_width if inference_width > 0 else 640,
        classes=[PERSON_CLASS_ID, MOTORCYCLE_CLASS_ID],
    )[0]

    people = []
    motorcycles = []

    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf = float(box.conf[0])
        if conf < confidence_threshold:
            continue

        coords = box.xyxy[0].tolist()
        if scale != 1.0:
            coords = [coord / scale for coord in coords]

        label = model.names[cls_id]
        if label == "person":
            people.append({"box": coords, "confidence": conf, "helmet": False, "is_rider": False})
        elif label in {"motorcycle", "motorbike"}:
            motorcycles.append({"box": coords, "confidence": conf})

    groups = _associate_people_to_bikes(people, motorcycles)

    for group in groups:
        for rider in group["riders"]:
            rider["is_rider"] = True
            rider["helmet"] = _approximate_helmet(frame, rider["box"])

    return people, motorcycles, groups


def _draw_panel(frame: np.ndarray, total_count: int, labels: Dict[str, int], timestamp: str) -> None:
    overlay = frame.copy()
    cv2.rectangle(overlay, (24, 20), (470, 210), (10, 12, 28), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    cv2.putText(frame, "AI Traffic Violation Detection", (42, 56), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (255, 255, 255), 2)
    cv2.putText(frame, f"Violations: {total_count}", (42, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 234, 255), 2)
    cv2.putText(frame, f"Triple Riding: {labels.get('Triple Riding', 0)}", (42, 124), cv2.FONT_HERSHEY_SIMPLEX, 0.63, (255, 123, 0), 2)
    cv2.putText(frame, f"No Helmet: {labels.get('No Helmet', 0)}", (42, 154), cv2.FONT_HERSHEY_SIMPLEX, 0.63, (255, 76, 129), 2)
    cv2.putText(frame, f"Rule Violation: {labels.get('Traffic Rule Violation', 0)}", (42, 184), cv2.FONT_HERSHEY_SIMPLEX, 0.63, (217, 72, 255), 2)
    cv2.putText(frame, timestamp, (frame.shape[1] - 250, frame.shape[0] - 18), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (210, 210, 210), 2)


def process_video(input_path: str, output_path: str, snapshot_dir: str) -> Dict[str, object]:
    model = _get_model()
    capture = cv2.VideoCapture(input_path)
    if not capture.isOpened():
        return {"success": False, "message": "Unable to open video file."}

    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)) or 1280
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)) or 720
    fps = capture.get(cv2.CAP_PROP_FPS)
    fps = fps if fps and not math.isnan(fps) and fps > 0 else 24.0

    writer = cv2.VideoWriter(
        output_path,
        cv2.VideoWriter_fourcc(*"mp4v"),
        fps,
        (width, height),
    )

    labels_counter = defaultdict(int)
    violation_snapshots = []
    frame_index = 0
    sample_interval = max(1, int(fps))
    detection_interval = _env_int("DETECTION_FRAME_SKIP", 5)
    inference_width = _env_int("DETECTION_INFERENCE_WIDTH", 480)
    confidence_threshold = _env_float("DETECTION_CONFIDENCE", 0.35)
    people = []
    motorcycles = []
    groups = []
    last_violation_snapshot_path = None
    last_violation_types = []
    last_violation_timestamp = None

    while True:
        ok, frame = capture.read()
        if not ok:
            break

        frame_violations = []
        check_frame = frame_index % sample_interval == 0
        should_detect = frame_index == 0 or frame_index % detection_interval == 0

        if should_detect:
            people, motorcycles, groups = _run_detection(
                model=model,
                frame=frame,
                inference_width=inference_width,
                confidence_threshold=confidence_threshold,
            )

        for person in people:
            x1, y1, x2, y2 = map(int, person["box"])
            if person["is_rider"]:
                has_helmet = person["helmet"]
                color = (73, 227, 180) if has_helmet else (60, 100, 255)
                label_text = "Rider + Helmet" if has_helmet else "Rider + No Helmet"
            else:
                color = (136, 148, 255)
                label_text = "Person"

            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, label_text, (x1, max(28, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.62, color, 2)

        for bike in motorcycles:
            x1, y1, x2, y2 = map(int, bike["box"])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 215, 0), 2)
            cv2.putText(frame, "Motorcycle", (x1, max(28, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 215, 0), 2)

        for group in groups:
            riders = group["riders"]
            bike_box = group["motorcycle"]["box"]
            bx1, by1, bx2, by2 = map(int, bike_box)
            rider_count = len(riders)
            has_no_helmet = rider_count > 0 and any(not rider.get("helmet", False) for rider in riders)
            is_triple = rider_count >= 3

            cv2.putText(
                frame,
                f"Riders: {rider_count}",
                (bx1, min(height - 20, by2 + 24)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
            )

            if is_triple:
                cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 128, 255), 4)
                cv2.putText(frame, "TRIPLE RIDING", (bx1, max(36, by1 - 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.82, (0, 128, 255), 3)

            if has_no_helmet:
                cv2.putText(frame, "NO HELMET", (bx1, min(height - 20, by2 + 52)), cv2.FONT_HERSHEY_SIMPLEX, 0.78, (255, 76, 129), 3)

            if check_frame and is_triple:
                labels_counter["Triple Riding"] += 1
                frame_violations.append("Triple Riding")

            if check_frame and has_no_helmet:
                labels_counter["No Helmet"] += 1
                frame_violations.append("No Helmet")

            if check_frame and is_triple and has_no_helmet:
                labels_counter["Traffic Rule Violation"] += 1
                frame_violations.append("Traffic Rule Violation")
                cv2.rectangle(frame, (bx1, by1), (bx2, by2), (255, 0, 180), 5)
                cv2.putText(frame, "TRAFFIC RULE VIOLATION", (bx1, min(height - 24, by2 + 80)), cv2.FONT_HERSHEY_SIMPLEX, 0.76, (255, 0, 180), 3)

        timestamp = datetime.now().strftime("%d %b %Y %I:%M:%S %p")
        total_count = labels_counter["Traffic Rule Violation"] or (labels_counter["Triple Riding"] + labels_counter["No Helmet"])
        _draw_panel(frame, total_count, labels_counter, timestamp)

        if frame_violations and check_frame:
            snapshot_name = f"violation_{frame_index}.jpg"
            snapshot_path = str(Path(snapshot_dir) / snapshot_name)
            cv2.imwrite(snapshot_path, frame)
            violation_snapshots.append(snapshot_name)
            last_violation_snapshot_path = snapshot_path
            last_violation_types = sorted(set(frame_violations))
            last_violation_timestamp = timestamp

        writer.write(frame)
        frame_index += 1

    capture.release()
    writer.release()

    labels = {key: int(value) for key, value in labels_counter.items()}
    if "Triple Riding" not in labels:
        labels["Triple Riding"] = 0
    if "No Helmet" not in labels:
        labels["No Helmet"] = 0
    if "Traffic Rule Violation" not in labels:
        labels["Traffic Rule Violation"] = 0

    mail_sent = False
    mail_error = ""
    email_enabled = os.getenv("ENABLE_EMAIL_ALERTS", "1") == "1"
    if email_enabled and last_violation_snapshot_path and any(labels.values()):
        mail_sent, mail_error = send_violation_alert(
            violation_types=last_violation_types,
            timestamp=last_violation_timestamp or datetime.now().strftime("%d %b %Y %I:%M:%S %p"),
            image_path=last_violation_snapshot_path,
            counts=labels,
        )

    mail_message = (
        "Alert email sent successfully."
        if mail_sent
        else (
            f"Violation detected, but alert email was not sent. Reason: {mail_error}"
            if any(labels.values())
            else "No violation email was sent because no alert condition was triggered."
        )
    )
    if any(labels.values()) and not email_enabled:
        mail_message = "Violation detected. Email alerts are disabled for faster analysis."

    return {
        "success": True,
        "message": "AI analysis completed successfully.",
        "mail_sent": mail_sent,
        "mail_error": mail_error,
        "mail_message": mail_message,
        "violation_count": labels["Traffic Rule Violation"] or (labels["Triple Riding"] + labels["No Helmet"]),
        "labels_detected": labels,
        "snapshots": [f"/outputs/snapshots/{name}" for name in violation_snapshots],
    }
