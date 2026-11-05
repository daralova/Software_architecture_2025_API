"""Adapter: любой источник кадров (RTSP-камера, файл) выглядит одинаково."""
import abc
import cv2

class FrameSource(abc.ABC):
    @abc.abstractmethod
    def frames(self):
        """Генератор пар (frame_index, BGR-кадр)."""

    def release(self):
        pass


class VideoFileSource(FrameSource):
    def __init__(self, path: str, stride: int = 1):
        self.cap = cv2.VideoCapture(path)
        self.stride = stride

    def frames(self):
        idx = 0
        while True:
            ok, frame = self.cap.read()
            if not ok:
                break
            if idx % self.stride == 0:
                yield idx, frame
            idx += 1

    def release(self):
        self.cap.release()


class RTSPSource(FrameSource):
    def __init__(self, url: str, stride: int = 1, reconnect_sec: int = 5):
        self.url, self.stride, self.reconnect_sec = url, stride, reconnect_sec

    def frames(self):
        import time
        while True:
            cap = cv2.VideoCapture(self.url)
            if not cap.isOpened():
                time.sleep(self.reconnect_sec)
                continue
            idx = 0
            running = True
            while running:
                ok, frame = cap.read()
                if not ok:
                    running = False
                    break
                if idx % self.stride == 0:
                    yield idx, frame
                idx += 1
            cap.release()
            time.sleep(self.reconnect_sec)  # авто-переподключение


def make_source(source: str, stride: int) -> FrameSource:
    if source.startswith(("rtsp://", "http://", "https://")):
        return RTSPSource(url=source, stride=stride)
    return VideoFileSource(path=source, stride=stride)
