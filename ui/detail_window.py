"""
Detail dialog that shows an enlarged card image together with rules text
and other meta-data.  Meant to be imported from ui.main_window or anywhere
else that needs it.
"""
from __future__ import annotations

from PyQt6 import QtCore, QtGui, QtWidgets
from core.image_loader import ImageLoader, ImageLoaderSignals
import os


class CardDetailDialog(QtWidgets.QDialog):
    """
    Modal window displaying the chosen card in a larger format plus text
    sections (type line, oracle text, flavour text, …).

    The dialog expects a *card* dictionary shaped like the Scryfall JSON
    response, optionally carrying cached QPixmaps under keys such as
    “pixmap_lg”, “pixmap_normal”, “pixmap_small”.
    """

    def __init__(
        self,
        card: dict,
        parent: QtWidgets.QWidget | None = None,
        cache_dir: str = "./resources/cache",
    ) -> None:
        super().__init__(parent, QtCore.Qt.WindowType.Dialog)
        self.setWindowTitle(card.get("name", "Card details"))
        self.setModal(True)
        self._thread_pool = QtCore.QThreadPool.globalInstance()
        self.image_loader_signals = ImageLoaderSignals()
        self.image_loader_signals.image_loaded.connect(self._on_image_loaded)
        self.image_loader_signals.image_error.connect(self._on_image_error)
        self._cache_dir = cache_dir

        # ------------------------------------------------------------------
        # Image section
        # ------------------------------------------------------------------
        self._img_lbl = QtWidgets.QLabel(
            alignment=QtCore.Qt.AlignmentFlag.AlignCenter
        )
        self._set_pixmap_from_card(card)

        # ------------------------------------------------------------------
        # Text section
        # ------------------------------------------------------------------
        text_edit = QtWidgets.QTextEdit(readOnly=True)
        text_edit.setPlainText(self._build_text(card))

        # ------------------------------------------------------------------
        # Layout
        # ------------------------------------------------------------------
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self._img_lbl, stretch=2)
        layout.addWidget(text_edit, stretch=1)

        # ------------------------------------------------------------------
        # Image handling
        # ------------------------------------------------------------------

    def _set_pixmap_from_card(self, card: dict) -> None:
        """
        Show the largest in-memory pixmap available, or download one through
        ImageLoader when it is not cached yet.
        """
        # 1) In-memory QPixmaps already attached to the card dict?
        for key in ("pixmap_lg", "pixmap_normal", "pixmap_small"):
            if (pix := card.get(key)) is not None:
                self._pixmap = pix
                self._img_lbl.setPixmap(pix)
                return  # nothing more to do

        # 2) Otherwise: start an ImageLoader job
        url = self._best_image_url(card)
        if not url:
            self._img_lbl.setText("No image available")
            return

        # display a temporary message while loading
        self._img_lbl.setText("Loading …")

        # Choose a reasonably large target size (pixels); ImageLoader will
        # keep the aspect ratio.
        target_size = QtCore.QSize(480, 672)

        # make sure the cache directory exists
        os.makedirs(self._cache_dir, exist_ok=True)

        loader = ImageLoader(
            url=url,
            cache_dir=self._cache_dir,
            thumb_size=target_size,
            signals=self.image_loader_signals,
        )
        self._thread_pool.start(loader)

    @QtCore.pyqtSlot(str, QtGui.QPixmap)
    def _on_image_loaded(self, url: str, pixmap: QtGui.QPixmap) -> None:
        """
        Slot connected to the ImageLoader’s finished signal.
        """
        self._pixmap = pixmap
        self._img_lbl.setPixmap(pixmap)

    @QtCore.pyqtSlot(str, str)
    def _on_image_error(self, url: str, error_message: str) -> None:
        self._img_lbl.setText(f"Failed to load image: {error_message}")
        self._img_lbl.setStyleSheet("color: red;")

    @staticmethod
    def _best_image_url(card: dict) -> str | None:
        uris = card.get("image_uris", {})
        for key in ("png", "large", "normal", "small"):
            if uris.get(key):
                return uris[key]
        faces = card.get("card_faces")
        if faces:
            for key in ("png", "large", "normal", "small"):
                if faces[0].get("image_uris", {}).get(key):
                    return faces[0]["image_uris"][key]
        return None

    @staticmethod
    def _build_text(card: dict) -> str:
        """Collect interesting textual fields."""
        parts: list[str] = []
        for key in ("type_line", "oracle_text", "flavor_text"):
            if value := card.get(key):
                parts.append(value)
        return "\n\n".join(parts)
