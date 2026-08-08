import time

import cv2


def main() -> None:
    print("Opening camera 0. If macOS asks for permission, allow it.")
    camera = cv2.VideoCapture(0)
    time.sleep(1)
    ok, frame = camera.read()
    print(f"camera_opened={camera.isOpened()}")
    print(f"frame_read={ok and frame is not None}")
    camera.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
