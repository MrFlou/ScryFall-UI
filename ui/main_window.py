from PyQt6 import QtWidgets, QtCore, QtGui
import os
import csv
from core.image_loader import ImageLoader, ImageLoaderSignals
from core.scryfall_api import ScryfallAPI
from utils.helpers import calculate_columns
from ui.config import GalleryConfig
from ui.detail_window import CardDetailDialog

class ScryfallGallery(QtWidgets.QMainWindow):
    def __init__(self, cache_dir='./resources/cache'):
        super().__init__()
        self.setWindowTitle('Scryfall Image Gallery')
        self.resize(1024, 768)

        # State
        self.page = 1
        self.has_more = False
        self.total_cards = 0
        self.thumb_width = GalleryConfig.THUMB_WIDTH
        self.aspect_ratio = GalleryConfig.ASPECT_RATIO
        self.thumb_size = QtCore.QSize(self.thumb_width, int(self.thumb_width * self.aspect_ratio))
        self.cache_dir = cache_dir
        os.makedirs(self.cache_dir, exist_ok=True)
        self.current_cards = []
        self.labels = {}

        self.collection_names = set()
        self.filter_enabled = False

        self.resize_timer = QtCore.QTimer(self)
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self._reposition_labels)

        self.pool = QtCore.QThreadPool.globalInstance()
        self.api = ScryfallAPI()

        self.image_loader_signals = ImageLoaderSignals()
        self.image_loader_signals.image_loaded.connect(self.set_image)
        self.image_loader_signals.image_error.connect(self._on_image_error)

        self.progressBar = QtWidgets.QProgressBar()
        self.progressBar.setVisible(False)
        self.lbl_total = QtWidgets.QLabel('')

        self._build_ui()

    def _build_ui(self):
        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        layout = QtWidgets.QVBoxLayout(central)

        self._create_control_widgets(layout)
        self._create_scroll_area(layout)
        self._create_navigation_buttons(layout)

        layout.addWidget(self.lbl_total)

    def _create_control_widgets(self, layout):
        ctrl_layout = QtWidgets.QHBoxLayout()
        self.query_edit = QtWidgets.QLineEdit()
        self.query_edit.setPlaceholderText('Enter Scryfall query')
        self.query_edit.returnPressed.connect(self.search)
        ctrl_layout.addWidget(self.query_edit)

        btn_search = QtWidgets.QPushButton('Search')
        btn_search.clicked.connect(self.search)
        ctrl_layout.addWidget(btn_search)

        btn_load = QtWidgets.QPushButton('Load Collection...')
        btn_load.clicked.connect(self.load_collection)
        ctrl_layout.addWidget(btn_load)

        self.archidekt_id_edit = QtWidgets.QLineEdit()
        self.archidekt_id_edit.setPlaceholderText('Archidekt Collection ID')
        ctrl_layout.addWidget(self.archidekt_id_edit)

        btn_load_archidekt = QtWidgets.QPushButton('Load Archidekt')
        btn_load_archidekt.clicked.connect(self.load_archidekt_collection)
        ctrl_layout.addWidget(btn_load_archidekt)

        self.chk_filter = QtWidgets.QCheckBox('Filter Collection')
        self.chk_filter.toggled.connect(self.toggle_filter)
        ctrl_layout.addWidget(self.chk_filter)

        ctrl_layout.addWidget(QtWidgets.QLabel('Thumb Width:'))
        self.slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.slider.setRange(50, 400)
        self.slider.setValue(self.thumb_width)
        self.slider.valueChanged.connect(self._on_slider_change)
        self.slider.sliderReleased.connect(self._on_slider_release)
        ctrl_layout.addWidget(self.slider)

        layout.addLayout(ctrl_layout)
        layout.addWidget(self.progressBar)

    def _create_scroll_area(self, layout):
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        container = QtWidgets.QWidget()
        self.grid = QtWidgets.QGridLayout(container)
        self.scroll.setWidget(container)
        layout.addWidget(self.scroll)

    def _create_navigation_buttons(self, layout):
        nav_layout = QtWidgets.QHBoxLayout()
        self.btn_prev = QtWidgets.QPushButton('<< Prev')
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_prev.setEnabled(False)
        nav_layout.addWidget(self.btn_prev)

        self.lbl_page = QtWidgets.QLabel('Page 1')
        nav_layout.addWidget(self.lbl_page)

        self.btn_next = QtWidgets.QPushButton('Next >>')
        self.btn_next.clicked.connect(self.next_page)
        self.btn_next.setEnabled(False)
        nav_layout.addWidget(self.btn_next)

        layout.addLayout(nav_layout)
    
    def load_collection(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, 'Open Collection CSV', '', 'CSV Files (*.csv)')
        if not path:
            return
        try:
            with open(path, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                self.collection_names = {row['Name'].strip() for row in reader if 'Name' in row}
            QtWidgets.QMessageBox.information(self, 'Collection Loaded', f'Loaded {len(self.collection_names)} names')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to load CSV: {e}')

    def load_archidekt_collection(self):
        collection_id_str = self.archidekt_id_edit.text().strip()
        if not collection_id_str:
            QtWidgets.QMessageBox.warning(self, 'Input Error', 'Please enter an Archidekt Collection ID.')
            return
        try:
            collection_id = int(collection_id_str)
            collection = self.api.get_archidekt_collection_from_api(collection_id)
            if collection:
                self.collection_names = {card['Name'].strip() for card in collection if 'Name' in card}
                QtWidgets.QMessageBox.information(self, 'Collection Loaded', f'Loaded {len(self.collection_names)} card names from Archidekt.')
            else:
                QtWidgets.QMessageBox.warning(self, 'Collection Not Found', 'Could not retrieve collection from Archidekt or it is empty.')
            if self.filter_enabled:
                self.search()
        except ValueError:
            QtWidgets.QMessageBox.critical(self, 'Input Error', 'Invalid Archidekt Collection ID. Please enter a number.')
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, 'Error', f'Failed to load Archidekt collection: {e}')

    def toggle_filter(self, enabled: bool):
        self.filter_enabled = enabled
        self.page = 1
        self._update_nav_buttons()
        self.search()

    def _on_slider_change(self, value):
        self.thumb_width = int(value)
        self.thumb_size = QtCore.QSize(self.thumb_width, int(self.thumb_width * self.aspect_ratio))

    def _on_slider_release(self):
        self._display_results(self.current_cards)

    def search(self):
        self.page = 1
        QtCore.QTimer.singleShot(0, self._perform_search)

    def prev_page(self):
        if not self.filter_enabled and self.page > 1:
            self.page -= 1
            QtCore.QTimer.singleShot(0, self._perform_search)

    def next_page(self):
        if not self.filter_enabled and self.has_more:
            self.page += 1
            QtCore.QTimer.singleShot(0, self._perform_search)

    def _perform_search(self):
        q = self.query_edit.text().strip()
        if not q:
            self._show_error('Please enter a search query')
            return
        try:
            if self.filter_enabled and self.collection_names:
                self.current_cards = self.api.filtered_search(q, self.collection_names)
                self.has_more = False
                self.total_cards = len(self.current_cards)
            else:
                data = self.api.search(q, self.page)
                self.current_cards = data.get('data', [])
                self.has_more = data.get('has_more', False)
                self.total_cards = data.get('total_cards', len(self.current_cards))
        except Exception as e:
            self._show_error(f'Error during search: {e}')
            return
        self._update_ui()

    def _update_ui(self):
        self.lbl_page.setText(f'Page {self.page} / {((self.total_cards - 1) // 175 + 1) if not self.filter_enabled else ""}')
        self.lbl_total.setText(
            f"Total cards in collection matching query: {len(self.current_cards)}" if self.filter_enabled else \
            f"Total cards matching query: {self.total_cards}"
        )
        self._update_nav_buttons()
        count = len(self.current_cards)
        self.progressBar.setMaximum(count)
        self.progressBar.setValue(0)
        self.progressBar.setVisible(True)
        self._display_results(self.current_cards)

    def _update_nav_buttons(self):
        self.btn_prev.setEnabled(self.page > 1 and not self.filter_enabled)
        self.btn_next.setEnabled(self.has_more and not self.filter_enabled)

    def _show_error(self, msg):
        QtWidgets.QMessageBox.critical(self, 'Error', msg)

    def resizeEvent(self, event):
        self.resize_timer.start(GalleryConfig.RESIZE_DELAY)
        super().resizeEvent(event)

    def _reposition_labels(self):
        if not self.current_cards:
            return
        for i in reversed(range(self.grid.count())):
            self.grid.takeAt(i)
        cols = calculate_columns(self.scroll.viewport().width(), self.thumb_width)
        for idx, card in enumerate(self.current_cards):
            url = self._get_best_image_url(card)
            lbl = self.labels.get(url)
            if lbl:
                row, col = divmod(idx, cols)
                self.grid.addWidget(lbl, row, col)

    # ------------------------------------------------------------------
    # NEW: slot to pop up the detail window
    # ------------------------------------------------------------------
    @QtCore.pyqtSlot(dict)
    def _show_card_details(self, card: dict) -> None:
        """
        Open a modal dialog that shows an enlarged image and the card’s
        rules text.  The dialog is defined in ui.detail_window.py.
        """
        CardDetailDialog(card, self, cache_dir=GalleryConfig.CACHE_DIR).exec()

    def _display_results(self, cards):
        while self.grid.count():
            widget = self.grid.takeAt(0).widget()
            if widget:
                widget.deleteLater()
        self.labels.clear()

        cols = calculate_columns(self.scroll.viewport().width(), self.thumb_width)
        for idx, card in enumerate(cards):
            row, col = divmod(idx, cols)

            url = self._get_best_image_url(card)

            # --- create a clickable label instead of a plain QLabel ----
            lbl = ClickableLabel(card)
            lbl.doubleClicked.connect(self._show_card_details)          # NEW
            lbl.setFixedSize(self.thumb_size)
            lbl.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

            self.grid.addWidget(lbl, row, col)
            self.labels[url] = lbl

            loader = ImageLoader(url, self.cache_dir, self.thumb_size, self.image_loader_signals)
            self.pool.start(loader)

    def _get_best_image_url(self, card):
        uris = card.get('image_uris', {})
        for key in ('png', 'large', 'normal', 'small'):
            if uris.get(key):
                return uris[key]
        faces = card.get('card_faces')
        if faces:
            for key in ('png', 'large', 'normal', 'small'):
                if faces[0].get('image_uris', {}).get(key):
                    return faces[0]['image_uris'][key]
        return None

    @QtCore.pyqtSlot(str, str)
    def _on_image_error(self, url: str, error_message: str) -> None:
        lbl = self.labels.get(url)
        if lbl:
            lbl.setText(f"Error: {error_message}")
            lbl.setStyleSheet("color: red;")
        val = self.progressBar.value() + 1
        self.progressBar.setValue(val)
        if val >= self.progressBar.maximum():
            self.progressBar.setVisible(False)

    @QtCore.pyqtSlot(str, QtGui.QPixmap)
    def set_image(self, url, pix):
        lbl = self.labels.get(url)
        if lbl:
            lbl.setPixmap(pix)
        val = self.progressBar.value() + 1
        self.progressBar.setValue(val)
        if val >= self.progressBar.maximum():
            self.progressBar.setVisible(False)

# --------------------------------------------------------------------
# NEW: Clickable Label
# --------------------------------------------------------------------
class ClickableLabel(QtWidgets.QLabel):
    doubleClicked = QtCore.pyqtSignal(dict)

    def __init__(self, card: dict, parent=None):
        super().__init__(parent)
        self.card = card

    def mouseDoubleClickEvent(self, event):
        self.doubleClicked.emit(self.card)