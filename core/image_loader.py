import hashlib, os, requests
from PyQt6 import QtCore, QtGui

class ImageLoader(QtCore.QRunnable):
    def __init__(self, url, cache_dir, thumb_size, signal):
        super().__init__()
        self.url = url
        self.cache_dir = cache_dir
        self.thumb_size = thumb_size
        self.signal = signal

    @QtCore.pyqtSlot()
    def run(self):
        key = hashlib.sha1(self.url.encode()).hexdigest()
        webp_path = os.path.join(self.cache_dir, f'{key}.webp')
        try:
            if os.path.exists(webp_path):
                pix = QtGui.QPixmap(webp_path)
            else:
                resp = requests.get(self.url)
                resp.raise_for_status()
                pix = QtGui.QPixmap()
                pix.loadFromData(resp.content)
                pix.save(webp_path, 'WEBP', quality=85)

            scaled = pix.scaled(
                self.thumb_size,
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            self.signal.emit(self.url, scaled)
        except Exception as e:
            print(f'[LOG] Failed to load {self.url}: {e}')
