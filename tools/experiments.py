"""
Prototype script to visualize grayscale and binarized versions of an input image.

Usage:
    python tools/image_masking_experiment.py /path/to/image.jpg

The script loads the provided image, converts it to grayscale, applies
Otsu's binarization, and opens pop-out windows for both the grayscale and
binarized results to help with debugging handwriting masking.


"""

import argparse
import sys
from pathlib import Path
import win32gui
import cv2


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Visualize grayscale and binarized versions of an image."
    )
    parser.add_argument(
        "image_path",
        type=Path,
        help="Path to the image file to process.",
    )
    parser.add_argument(
        "--block-size",
        type=int,
        default=35,
        help=(
            "Block size for adaptive thresholding (must be odd and > 1). "
            "Set to 0 to use global Otsu thresholding instead."
        ),
    )
    parser.add_argument(
        "--c",
        type=int,
        default=10,
        help=(
            "Constant subtracted from the mean in adaptive thresholding. "
            "Ignored when using global Otsu thresholding."
        ),
    )
    return parser.parse_args()


def load_image(image_path: Path) -> cv2.Mat:
    if not image_path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    image = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"Unable to read image: {image_path}")
    return image


def to_grayscale(image: cv2.Mat) -> cv2.Mat:
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

def binarize_image(gray_image: cv2.Mat, block_size: int, c: int) -> cv2.Mat:
    if block_size <= 0:
        # Use global threshold with Otsu's method.
        _, binary = cv2.threshold(
            gray_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )
        return binary

    if block_size % 2 == 0 or block_size <= 1:
        raise ValueError("block_size must be an odd integer greater than 1")

    return cv2.adaptiveThreshold(
        gray_image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c,
    )


def show_images(gray_image: cv2.Mat, binary_image: cv2.Mat) -> None:
    cv2.imshow("Grayscale", gray_image)
    cv2.imshow("Binarized", binary_image)
    print("Press any key while the image windows are focused to close them...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def main() -> None:
    args = parse_args()
    try:
        image = load_image(args.image_path)
        gray_image = to_grayscale(image)
        binary_image = binarize_image(gray_image, args.block_size, args.c)
    except Exception as exc:  # noqa: BLE001
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    show_images(gray_image, binary_image)


def get_window_init_pisition(game_title: str) -> tuple[int, int, int, int]:
    """取得視窗初始位置"""
    hwnd = win32gui.FindWindow(None, game_title)
    if not hwnd:
        raise RuntimeError(f"沒匹配指定的視窗: {game_title}")
    print(f"成功讀取遊戲標題: {game_title}，視窗句柄: {hwnd}")
    
    rect = win32gui.GetWindowRect(hwnd)
    win_left, win_top, win_right, win_bottom = rect
    return win_left, win_top, win_right, win_bottom

if __name__ == "__main__":
    main()