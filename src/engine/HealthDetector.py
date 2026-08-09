import cv2
import logging
from config.config_loader import config
from src.utils.common import draw_dectection_box
class HealthDetector():
    def __init__(self) -> None:
        hp_bar = config.get("health_detector.hp_lect")
