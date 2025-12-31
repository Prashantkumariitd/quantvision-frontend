import mss
import numpy as np
import cv2
from .config import CAPTURE_REGION


def grab_chart_frame() -> "np.ndarray":
    """
    Capture a frame of the configured chart region.
    Returns a BGR OpenCV image.
    """
    with mss.mss() as sct:
        monitor = {
            "left": CAPTURE_REGION["left"],
            "top": CAPTURE_REGION["top"],
            "width": CAPTURE_REGION["width"],
            "height": CAPTURE_REGION["height"],
        }
        sct_img = sct.grab(monitor)
        frame = np.array(sct_img)[:, :, :3]  # drop alpha channel
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame
