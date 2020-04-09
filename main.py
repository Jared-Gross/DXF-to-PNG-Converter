from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import *
from PyQt5 import QtWidgets, uic, QtPrintSupport
from functools import partial
from dxf2svg.pycore import save_svg_from_dxf, extract_all
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from shutil import copyfile
from PIL import Image
import sys, os, json, cv2, time, threading,ezdxf

Data_JSON = "data.json"
Data_JSON_Contents = []

file_names = []
image_locations = []
quantities = []
class ConvertThread(QThread):
    
    data_downloaded = pyqtSignal(object)

    def __init__(self, file):
        QThread.__init__(self)
        self.file = file

    def run(self):
        # j = self.file
        self.data_downloaded.emit(f'1/{len(self.file)} - Starting.')
        time.sleep(1)
        for i, j in enumerate(self.file):
            print(j)
            # Generate file name
            temp_fileName = j.split("/")
            temp_fileName = temp_fileName[-1]
            temp_fileName = temp_fileName.split(".")
            temp_fileName = temp_fileName[0]
            # Gnerate file Location
            imgLoc = os.path.dirname(os.path.abspath(__file__)) + '/Images/' + temp_fileName + '.png'
            imgLoc = imgLoc.replace('\\','/')
            imgLoc = imgLoc.split('/')
            imgLoc[0] = imgLoc[0].capitalize()
            imgLoc = '/'.join(imgLoc)
            

            # Check if file already exists
            for o, k in enumerate(image_locations):
                if k == imgLoc:
                    # buttonReply = QMessageBox.critical(self, 'File already exists', f"{temp_fileName}.DXF already exists!\n\nWould you like to overwrite {temp_fileName}?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Yes)
                    # if buttonReply == QMessageBox.No: continue
                    # elif buttonReply == QMessageBox.Cancel: return
                    # elif buttonReply == QMessageBox.Yes:
                    # if os.path.exists(k): os.remove(k)
                    Data_JSON_Contents.pop(o)

            dxffilepath = j

            #self.lblState.setText("Getting dimensions.")
            self.data_downloaded.emit(f'{i+1}/{len(self.file)} - {temp_fileName} - Extracting {temp_fileName}.DXF..')
            # Force command to run, and halt the program untill the process is finished
            os.popen(f'dia \"{j}\" -e properties.png').read()
            # p = subprocess.Popen(f'dia \"{j}\" -e properties.png')
            # p.communicate() #now wait plus that you can send commands to process
            # time.sleep(5)
            # while os.path.exists("properties.png"):
            # time.sleep(1)
            # Get data from DXF FILE
            im = cv2.imread('properties.png')
            h, w, c = im.shape
            print('width:  ', w)
            print('height: ', h)
            if w > h: s = w
            else: s = h

            # convert DXF file to PNG
            # #self.lblState.setText("Extracting DXF..")
            self.data_downloaded.emit(f'{i+1}/{len(self.file)} - {temp_fileName} - Converting {temp_fileName}.DXF to PNG...')
            copyfile(dxffilepath, "clone.DXF")
            extract_all('clone.DXF')
            drawing = svg2rlg('clone.DXF')
            # #self.lblState.setText("Converting DXF...")
            renderPM.drawToFile(drawing, f"Images/{temp_fileName}.png", fmt="PNG")

            # #self.lblState.setText("Finalizing image....")
            self.data_downloaded.emit(f'{i+1}/{len(self.file)} - {temp_fileName} - Finalizing image....')
            # Make image black and white
            originalImage = cv2.imread(imgLoc)
            originalImage = cv2.resize(originalImage, (int(w/2), int(h/2)))
            originalImage = cv2.GaussianBlur(originalImage,(3,1),0)


            (thresh, blackAndWhiteImage) = cv2.threshold(originalImage, 250, 255, cv2.THRESH_BINARY)
            cv2.imwrite(f"{imgLoc}", blackAndWhiteImage)

            top, bottom, left, right = 50, 50, 50 ,50
            color = (255, 255, 255)
            # add margin
            im = Image.open(imgLoc)
            width, height = im.size
            new_width = width + right + left
            new_height = height + top + bottom
            result = Image.new(im.mode, (new_width, new_height), color)
            result.paste(im, (left, top))
            result.save(imgLoc, quality=95)
            
            top, bottom, left, right = int(50/5),  int(50/5), int(50/5), int(50/5)
            color = (0, 0, 0)
            im = Image.open(imgLoc)
            width, height = im.size
            new_width = width + right + left
            new_height = height + top + bottom
            result = Image.new(im.mode, (new_width, new_height), color)
            result.paste(im, (left, top))
            result.save(imgLoc, quality=95)
            
            # #self.lblState.setText("Saving.....")
            self.data_downloaded.emit(f'{i+1}/{len(self.file)} - {temp_fileName} - Saving.....')
            Data_JSON_Contents.append({
            'fileName': [temp_fileName],
            'imgLoc': [imgLoc],
            'quantity':[1]
            })
            # save data to JSON file
            sortedList = sorted(Data_JSON_Contents, key = lambda i: i['fileName'])
            with open(Data_JSON, mode='w+', encoding='utf-8') as file: json.dump(sortedList, file, ensure_ascii=True, indent=4, sort_keys=True)
            # self.progressBar.setValue(i+1)
            
            # Reload GUI
            # info = urllib2.urlopen(self.url).info()
            # self.data_downloaded.emit('%s\n%s' % (self.url, info))
        
        os.remove('properties.png')
        os.remove('clone.DXF')
        self.data_downloaded.emit('Finished!')
        time.sleep(1)
        self.data_downloaded.emit('')

class mainwindowUI(QMainWindow):
    def __init__(self, parent = None):
        super(mainwindowUI, self).__init__(parent)
        uic.loadUi('MainWindow.ui', self)
        self.lastTextBoxInFucos = 0
        self.setStyleSheet(open("style.qss", "r").read())
        
        self.btnAdd = self.findChild(QPushButton, 'btnAdd')
        self.btnAdd.clicked.connect(self.add)
        
        self.lblState = self.findChild(QLabel,'lblState')
        #self.lblState.setText("")
        
        self.actionPrint = self.findChild(QAction, 'actionPrint')
        self.actionPrint.triggered.connect(self.print_widget)
        
        self.actionPrint = self.findChild(QAction, 'action_Add')
        self.actionPrint.triggered.connect(self.add)
        
        self.clearLayout(self.gridLayoutItems)
        self.reloadListUI()
        # self.print_widget()
        self.show()
    def start_conversion(self, files):
        self.threads = []
        converter = ConvertThread(files)
        converter.data_downloaded.connect(self.on_data_ready)
        self.threads.append(converter)
        converter.start()
    def on_data_ready(self, text):
        self.lblState.setText(f"{text}")
        self.clearLayout(self.gridLayoutItems)
        self.reloadListUI()
    def add(self):
        # open file directory
        files, _ = QFileDialog.getOpenFileNames(self,"Add Files", "","DXF Files (*.dxf)")
        existing_files = []
        non_existing_files = []
        if files:
            print(files)
            temp_fileNames = []
            for i, j in enumerate(files):
                # Generate file name
                temp_fileName = j.split("/")
                temp_fileName = temp_fileName[-1]
                temp_fileName = temp_fileName.split(".")
                temp_fileName = temp_fileName[0]
                temp_fileNames.append(temp_fileName)
                
                # else:
                #     buttonReply = QMessageBox.critical(self, 'File already exists', f"{j}.DXF already exists!\n\nWould you like to overwrite {j}?", QMessageBox.YesToAll | QMessageBox.Yes | QMessageBox.Abort, QMessageBox.YesToAll)
                #     if buttonReply == QMessageBox.Abort: return
                #     elif buttonReply == QMessageBox.Yes: break
                    # elif buttonReply == QMessageBox.YesToAll:
                        # Loop over all items and do it automaticly
            set_1 = set(temp_fileNames)
            non_existing_files = [item for item in set_1 if item not in file_names]
            print('\n')
            print(existing_files)
            print('\n')
            print(non_existing_files)
            self.start_conversion(files)
    def openImage(self, path):
        # threading.Thread(target=self.startThreadOpenImage,args=(path,)).start()
        # def startThreadOpenImage(self, path):
        self.vi = view_image(path)
        self.vi.show()
        self.close()
    def delete(self, path):
        for o, k in enumerate(image_locations):
            if k == path:
                if os.path.exists(k): os.remove(k)
                Data_JSON_Contents.pop(o)
                sortedList = sorted(Data_JSON_Contents, key = lambda i: i['fileName'])
                with open(Data_JSON, mode='w+', encoding='utf-8') as file: json.dump(sortedList, file, ensure_ascii=True, indent=4, sort_keys=True)
        self.clearLayout(self.gridLayoutItems)
        self.reloadListUI()
    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None: widget.deleteLater()
                else: self.clearLayout(item.layout())
    def print_widget(self):
        # Create printer
        printer = QtPrintSupport.QPrinter()
        # Create painter
        painter = QtGui.QPainter()
        # Start painter
        painter.begin(printer)
        # Grab a widget you want to print
        screen = self.grab()
        # Draw grabbed pixmap
        painter.drawPixmap(10, 10, screen)
        # End painting
        painter.end()
    def reloadListUI(self):
        load_data_file(file_names, image_locations, quantities)
        textBoxList = []
        label = QLabel("Name:")
        self.gridLayoutItems.addWidget(label, 0, 0)
        label = QLabel("Quantity:")
        self.gridLayoutItems.addWidget(label, 0, 1)
        label = QLabel("Thumbnail:")
        self.gridLayoutItems.addWidget(label, 0, 2)
        for i, j in enumerate(file_names):
            label = QLabel(j)
            # label.setFixedSize(128,20)
            self.gridLayoutItems.addWidget(label, i+1, 0)
            
            textBoxInput = QLineEdit("1")
            textBoxInput.setValidator(QIntValidator())
            textBoxInput.setText(str(quantities[i]))
            textBoxInput.editingFinished.connect(partial(self.saveLineEdit, textBoxInput, i))
            textBoxInput.setFocusPolicy(Qt.StrongFocus)
            textBoxList.append(textBoxInput)
            # textBoxInput.setFixedSize(64,20)
            self.gridLayoutItems.addWidget(textBoxInput, i+1, 1)
            
            btnImage = QPushButton()
            btnImage.clicked.connect(partial(self.openImage, image_locations[i]))
            btnImage.setIcon(QIcon(image_locations[i]))
            btnImage.setIconSize(QSize(256,100))
            # btnImage.setFixedSize(64,64)
            btnImage.setFlat(True)
            self.gridLayoutItems.addWidget(btnImage, i+1, 2)
            
            btnDelete = QPushButton()
            btnDelete.setFixedSize(50,50)
            btnDelete.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogDiscardButton')))
            btnDelete.clicked.connect(partial(self.delete, image_locations[i]))
            self.gridLayoutItems.addWidget(btnDelete, i+1, 3)
        
        if textBoxList: textBoxList[self.lastTextBoxInFucos].setFocus()
        # print(self.lastTextBoxInFucos)
        # self.gridLayoutItems.setColumnStretch(3,0)
    def saveLineEdit(self, textBox, index):
        self.newQuantity = textBox.text()
        if '.' in self.newQuantity:
            QMessageBox.critical(self, 'Must be an integer.', "Must be a whole number.\n\nNo decimal places", QMessageBox.Ok, QMessageBox.Ok)
            return
        elif self.newQuantity == '':
            return
        temp_path = image_locations[index]
        temp_name = file_names[index]
        Data_JSON_Contents.pop(index)
        Data_JSON_Contents.append({
        'fileName': [temp_name],
        'imgLoc': [temp_path],
        'quantity':[int(self.newQuantity)]
        })
        # save data to JSON file
        sortedList = sorted(Data_JSON_Contents, key = lambda i: i['fileName'])
        with open(Data_JSON, mode='w+', encoding='utf-8') as file: json.dump(sortedList, file, ensure_ascii=True, indent=4, sort_keys=True)
        self.lastTextBoxInFucos = index
        self.clearLayout(self.gridLayoutItems)
        self.reloadListUI()
class view_image(QtWidgets.QWidget):
    def __init__(self, directory_to_open,):
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
    def closeEvent(self, event):
        self.mm = mainwindowUI()
        self.mm.show()
        self.close()
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
        for info in Data_JSON_Contents:
            for name in info['fileName']: file_names.append(name)
            for path in info['imgLoc']: image_locations.append(path)
            for quan in info['quantity']: quantities.append(quan)

if __name__ == '__main__':
    if not os.path.exists('Images'): os.makedirs('Images')
    file_exists = os.path.isfile(Data_JSON)
    if file_exists: load_data_file(file_names, image_locations, quantities)
    else:
        f = open(Data_JSON, "w+")
        f.write("[]")
    app = QApplication(sys.argv)
    window = mainwindowUI()
    app.exec_()
