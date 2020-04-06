from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import *
from PyQt5 import QtWidgets, uic
from functools import partial
from dxf2svg.pycore import save_svg_from_dxf, extract_all
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from shutil import copyfile
import sys, os, json

Data_JSON = "data.json"
Data_JSON_Contents = []

file_names = []
image_locations = []

class mainwindowUI(QMainWindow):
    def __init__(self, parent = None):
        super(mainwindowUI, self).__init__(parent)
        uic.loadUi('MainWindow.ui', self)
        self.setStyleSheet(open("style.qss", "r").read())

        self.btnAdd = self.findChild(QPushButton, 'btnAdd')
        self.btnAdd.clicked.connect(self.add)
        
        self.show()
    def add(self):
        files, _ = QFileDialog.getOpenFileNames(self,"Add Files", "","DXF Files (*.dxf)")
        if files:
            for i, j in enumerate(files):
                temp_fileName = j.split("/")
                temp_fileName = temp_fileName[-1]
                temp_fileName = temp_fileName.split(".")
                temp_fileName = temp_fileName[0]
                
                imgLoc = j.split("/")
                imgLoc.pop(-1)
                imgLoc = '/'.join(imgLoc)
                imgLoc = imgLoc + '/Images/' + temp_fileName + '.png'
                
                dxffilepath = j
                
                copyfile(dxffilepath, "clone.DXF")
                extract_all('clone.DXF', size=256)
                drawing = svg2rlg('clone.DXF')
                renderPM.drawToFile(drawing, f"Images/{temp_fileName}.png", fmt="PNG")
                
                Data_JSON_Contents.append({
                'fileName': [temp_fileName],
                'imgLoc': [imgLoc]
                })
                # sort json file
                # sorted_saved_batches_data = sorted(saved_batches_data, key=itemgetter('thickness'), reverse=True)
                with open(Data_JSON, mode='w+', encoding='utf-8') as file:
                    json.dump(Data_JSON_Contents, file, ensure_ascii=True, indent=4, sort_keys=True)

    def openImage(self):
        self.vi = view_image(self.pdf_location)
        self.vi.show()

class view_image(QtWidgets.QWidget):
    def __init__(self, directory_to_open):
        super(view_image, self).__init__()
        self.image_to_open = directory_to_open
        directory_to_open = directory_to_open.replace('\\','/')
        self.setWindowTitle(directory_to_open)
        self.viewer = PhotoViewer(self)
        # self.resize(width, height)
        screen = app.primaryScreen()
        rect = screen.availableGeometry()
        self.setGeometry(0, 0, rect.width(), rect.height())
        self.viewer.photoClicked.connect(self.photoClicked)
        # Arrange layout
        VBlayout = QVBoxLayout(self)
        VBlayout.addWidget(self.viewer)
        HBlayout = QHBoxLayout()
        HBlayout.setAlignment(Qt.AlignLeft)
        VBlayout.addLayout(HBlayout)
        self.loadImage()
    def loadImage(self):
        self.viewer.setPhoto(QPixmap(self.image_to_open))
        self.showMaximized()
    def pixInfo(self):
        self.viewer.toggleDragMode()
    def photoClicked(self, pos):
        if self.viewer.dragMode()  == QGraphicsView.NoDrag:
            self.editPixInfo.setText('%d, %d' % (pos.x(), pos.y()))
class PhotoViewer(QtWidgets.QGraphicsView):
    photoClicked = pyqtSignal(QPoint)
    def __init__(self, parent):
        super(PhotoViewer, self).__init__(parent)
        self._zoom = 100
        self._empty = True
        self._scene = QGraphicsScene(self)
        self._photo = QGraphicsPixmapItem()
        self._scene.addItem(self._photo)
        self.setScene(self._scene)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
        self.setFrameShape(QFrame.NoFrame)
    def hasPhoto(self):
        return not self._empty
    def fitInView(self, scale=True):
        rect = QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(),
                             viewrect.height() / scenerect.height())
                self.scale(factor, factor)
            self._zoom = 0
    def setPhoto(self, pixmap=None):
        self._zoom = 100
        if pixmap and not pixmap.isNull():
            self._empty = False
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            self._photo.setPixmap(pixmap)
        else:
            self._empty = True
            self.setDragMode(QGraphicsView.NoDrag)
            self._photo.setPixmap(QPixmap())
        self.fitInView()
    def wheelEvent(self, event):
        if self.hasPhoto():
            if event.angleDelta().y() > 0:
                factor = 1.25
                self._zoom += 1
            else:
                factor = 0.8
                self._zoom -= 1
            if self._zoom > 0:
                self.scale(factor, factor)
            elif self._zoom == 0:
                self.fitInView()
            else:
                self._zoom = 0
    def toggleDragMode(self):
        if self.dragMode() == QGraphicsView.ScrollHandDrag:
            self.setDragMode(QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull():
            self.setDragMode(QGraphicsView.ScrollHandDrag)
    def mousePressEvent(self, event):
        if self._photo.isUnderMouse():
            self.photoClicked.emit(self.mapToScene(event.pos()).toPoint())
        super(PhotoViewer, self).mousePressEvent(event)
def load_data_file(*args):
    global Data_JSON_Contents
    for i, j in enumerate(args):
        j.clear()
        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
            # for name in Data_JSON_Contents[0]['fileName']: args[0].append(name)
            # for imgLoc in Data_JSON_Contents[0]['imgLoc']: args[1].append(imgLoc)
            # for info in Data_JSON_Contents:
            for name in Data_JSON_Contents['fileName']:
                file_names.append(name)
            for path in Data_JSON_Contents['imgLoc']:
                image_locations.append(path)
if __name__ == '__main__':
    if not os.path.exists('Images'): os.makedirs('Images')
    file_exists = os.path.isfile(Data_JSON)
    if file_exists:
        load_data_file(file_names, image_locations)
    else:
        f = open(Data_JSON, "w+")
        f.write("[]")
    app = QApplication(sys.argv)
    window = mainwindowUI()
    app.exec_()