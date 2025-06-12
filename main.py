import sys
from PyQt6 import QtWidgets
from ui.main_window import ScryfallGallery

def main():
    app = QtWidgets.QApplication(sys.argv)
    gallery = ScryfallGallery()
    gallery.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
