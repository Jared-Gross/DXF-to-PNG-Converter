from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import *
from PyQt5 import uic, QtPrintSupport
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5 import QtCore, QtWidgets, QtPrintSupport, QtGui
from functools import partial

from dxf2png.dxf2svg.pycore import save_svg_from_dxf, extract_all
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM
from shutil import copyfile
import sys, os, json, cv2, time, threading,ezdxf, imutils
import numpy as np
Data_JSON = "data.json"
Data_JSON_Contents = []

file_names = []
image_locations = []
quantities = []
window_geometry = [100, 200, 800, 600]
class ConvertThread(QThread):  
    data_downloaded = pyqtSignal(object)
    def __init__(self, file):
        QThread.__init__(self)
        self.file = file
    def run(self):
        # j = self.file
        self.data_downloaded.emit(f'1/{len(self.file)} - Starting.')
        # time.sleep(1)
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
            
            dxffilepath = j

            self.data_downloaded.emit(f'{i+1}/{len(self.file)} - {temp_fileName} - Extracting {temp_fileName}.DXF..')
            # Force command to run, and halt the program untill the process is finished
            os.popen(f'dia \"{dxffilepath}\" -e properties.png').read()

            # Get data from DXF FILE
            im = cv2.imread('properties.png')
            hei, wid, c = im.shape
            print('width:  ', wid)
            print('height: ', hei)
            if wid > hei: s = wid
            else: s = hei

            # convert DXF file to PNG
            self.data_downloaded.emit(f'{i+1}/{len(self.file)} - {temp_fileName} - Converting {temp_fileName}.DXF to PNG...')
            copyfile(dxffilepath, "clone.DXF")
            extract_all('clone.DXF',size = 512)
            # else: extract_all('clone.DXF', size = s)
            drawing = svg2rlg('clone.DXF')
            renderPM.drawToFile(drawing, imgLoc, fmt="PNG")
    
            self.data_downloaded.emit(f'{i+1}/{len(self.file)} - {temp_fileName} - Finalizing image....')
                
            # Make image black and white
            originalImage = cv2.imread(imgLoc)
            if s < 400:
                if wid > hei: originalImage = self.image_resize(originalImage, width = 512)
                else: originalImage = self.image_resize(originalImage, height = 512)
            # find all the 'black' shapes in the image
            lower = np.array([0, 0, 0])
            upper = np.array([250, 250, 250])
            originalImage = cv2.inRange(originalImage, lower, upper)
            originalImage = (255-originalImage)
            # originalImage = cv2.GaussianBlur(originalImage,(3,1),0)
            # (thresh, blackAndWhiteImage) = cv2.threshold(originalImage, 250, 255, cv2.THRESH_BINARY)
            cv2.imwrite(imgLoc,originalImage)
            # if wid < 500 and hei < 500:
            img = cv2.imread(imgLoc)
            # convert img to grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # invert polarity
            gray = 255 - gray
            # do adaptive threshold on gray image
            thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY)[1]
            # Get contours
            cnts = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0] if len(cnts) == 2 else cnts[1]
            # for c in cnts:
            # create white image
            result = np.full_like(img, (255,255,255))
            # get bounding box
            x,y,w,h = cv2.boundingRect(cnts[0])
            # crop region of img using bounding box
            region = img[y:y+h, x:x+w]
            
            lower = np.array([0, 0, 0])
            upper = np.array([250, 250, 250])
            region = cv2.inRange(region, lower, upper)
            region = (255-region)
            # save region to new image
            if s < 500: region = cv2.resize(region, (int(wid), int(hei)))
            else: region = cv2.resize(region, (int(wid/2), int(hei/2)))
            if hei > wid: region = imutils.rotate_bound(region, 90)
            cv2.imwrite(imgLoc, region)

            img = cv2.imread(imgLoc)
            img = cv2.copyMakeBorder(img.copy(),10,10,10,10,cv2.BORDER_CONSTANT,value=[255,255,255])
            img = self.image_resize(img, width=512)
            cv2.imwrite(imgLoc, img)
            region = cv2.imread(imgLoc)
            region = cv2.inRange(region, lower, upper)
            region = (255-region)
            cv2.imwrite(imgLoc, region)
            self.data_downloaded.emit(f'{i+1}/{len(self.file)} - {temp_fileName} - Saving.....')
            Data_JSON_Contents.append({
            'fileName': [temp_fileName],
            'imgLoc': [imgLoc],
            'quantity':[1]
            })
            # save data to JSON file
            sortedList = sorted(Data_JSON_Contents, key = lambda i: i['fileName'])
            with open(Data_JSON, mode='w+', encoding='utf-8') as file: json.dump(sortedList, file, ensure_ascii=True, indent=4, sort_keys=True)
        
        os.remove('properties.png')
        os.remove('clone.DXF')
        self.data_downloaded.emit('Finished!')
        time.sleep(1)
        self.data_downloaded.emit('')
        
    def image_resize(self, image, width = None, height = None, inter = cv2.INTER_AREA):
        # initialize the dimensions of the image to be resized and
        # grab the image size
        dim = None
        (h, w) = image.shape[:2]
        # if both the width and height are None, then return the
        # original image
        if width is None and height is None:
            return image
        # check to see if the width is None
        if width is None:
            # calculate the ratio of the height and construct the
            # dimensions
            r = height / float(h)
            dim = (int(w * r), height)
        # otherwise, the height is None
        else:
            # calculate the ratio of the width and construct the
            # dimensions
            r = width / float(w)
            dim = (width, int(h * r))
        # resize the image
        resized = cv2.resize(image, dim, interpolation = inter)
        # return the resized image
        return resized
        
class mainwindowUI(QMainWindow):
    resized = QtCore.pyqtSignal()
    def __init__(self, parent = None):
        super(mainwindowUI, self).__init__(parent)
        uic.loadUi('JordanProgramListOrginizer/mainwindow.ui', self)
        self.printer = QPrinter()
        self.setAcceptDrops(True)
        self.setGeometry(window_geometry[0],window_geometry[1],window_geometry[2],window_geometry[3])
        self.resized.connect(self.getSize)
        
        self.txtBoxList = []
        self.lastTextBoxInFucos = 0
        self.setStyleSheet(open("style.qss", "r").read())
        
        self.btnAdd = self.findChild(QPushButton, 'btnAdd')
        self.btnAdd.setObjectName('btnAdd')
        self.btnAdd.clicked.connect(partial(self.add, True, ''))
        self.btnAdd.setShortcut('Ctrl+O')

        # saveShortcut = QShortcut(QKeySequence("Ctrl+s"), self)
        # saveShortcut.activated.connect(self.save) 
        
        self.txtSearch = self.findChild(QLineEdit, 'txtSearch')
        self.txtSearch.editingFinished.connect(self.search)
        
        self.lblState = self.findChild(QLabel,'lblState')
        self.lblState.setHidden(True)
        
        self.progressBar = self.findChild(QProgressBar, 'progressBar')
        self.progressBar.setHidden(True)
        self.progressBar.setAlignment(QtCore.Qt.AlignLeft)
        
        self.actionPrint = self.findChild(QAction, 'actionPrint')
        self.actionPrint.triggered.connect(self.print_widget)
        self.actionPrint.setShortcut('Ctrl+P')
        
        self.actionAbout = self.findChild(QAction, 'actionAbout_2')
        self.actionAbout.triggered.connect(self.openAbout)
        self.actionAbout.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogInfoView')))

        self.actionAbout_Qt = self.findChild(QAction, 'actionAbout_Qt')
        self.actionAbout_Qt.triggered.connect(qApp.aboutQt)
        
        self.actionAdd = self.findChild(QAction, 'action_Add')
        self.actionAdd.triggered.connect(partial(self.add, True, ''))
        self.actionAdd.setShortcut('Ctrl+A')
        
        self.actionSave = self.findChild(QAction, 'action_Save')
        self.actionSave.triggered.connect(self.save)
        self.actionSave.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogSaveButton')))
        self.actionSave.setShortcut('Ctrl+S')
        self.clearLayout(self.gridLayoutItems)
        self.reloadListUI('')

        # self.print_widget()
        
        self.show()
    def resizeEvent(self, event):
        self.resized.emit()
        return super(mainwindowUI, self).resizeEvent(event)
    def getSize(self):
        global window_geometry
        window_geometry = [self.pos().x(), self.pos().y(), self.frameGeometry().width(), self.frameGeometry().height()]
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls: event.accept()
        else: event.ignore()
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else: event.ignore()
    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                links.append(str(url.toLocalFile()))
            self.add(False, links)
        else: event.ignore()
    def start_conversion(self, files):
        self.threads = []
        converter = ConvertThread(files)
        converter.data_downloaded.connect(self.on_data_ready)
        self.threads.append(converter)
        converter.start()
    def on_data_ready(self, text):
        try:
            # self.lblState.setHidden(False)
            self.progressBar.setHidden(False)
            self.lblState.setText(f"{text}")
            if not text == 'Finished!':
                if not text == '':
                    currentNum = text.split('/')
                    currentNum = int(currentNum[0])
                    
                    maxnum = text.split('/')
                    maxnum = maxnum[1]
                    maxnum = maxnum.split(' - ')
                    maxnum = int(maxnum[0])
                    
                    self.progressBar.setValue(currentNum)
                    self.progressBar.setMaximum(maxnum)
            self.progressBar.setFormat(' ' + text)
            if text == '': 
                self.clearLayout(self.gridLayoutItems)
                self.reloadListUI('')
                self.progressBar.setHidden(True)
        except Exception as e:
            print(e)
    def add(self, openFileDirectory, dragDropFiles):
        # open file directory
        if openFileDirectory: files, _ = QFileDialog.getOpenFileNames(self,"Add Files", "","DXF Files (*.dxf)")
        else: files = dragDropFiles
        print(files)
        existing_files = []
        non_existing_files = []
        approved = ['.dxf', '.DXF']
        files[:] = [url for url in files if any(sub in url for sub in approved)]
        # for i, j in enumerate(files):
        #     if j.endswith('.dxf') or j.endswith('.DXF'):
        #         pass
        #     else:
        #         files.pop(i)
        if files:
            temp_fileNames = []
            for i, j in enumerate(files):
                # Generate file name
                temp_fileName = j.split("/")
                temp_fileName = temp_fileName[-1]
                temp_fileName = temp_fileName.split(".")
                temp_fileName = temp_fileName[0]
                temp_fileNames.append(temp_fileName)
            # idk what this does but it works and it makes it faster they say
            set_1 = set(temp_fileNames)
            # add all files to this list if it does not exist in the data.json file
            non_existing_files = [item for item in set_1 if item not in file_names]
            # add all files to this list if they already have been added before
            existing_files = [item for item in set_1 if item in file_names]
            non_existing_files_index = []
            new_files = []
            # loop over all files that already exist
            for i, j in enumerate(existing_files):
                buttonReply = QMessageBox.critical(self, f'{files[i]}', f"A file named '{j}.DXF' already exists.\n\nDo you want to replace it?", QMessageBox.YesToAll | QMessageBox.Yes | QMessageBox.Abort, QMessageBox.YesToAll)
                if buttonReply == QMessageBox.Abort: return
                elif buttonReply == QMessageBox.Yes: 
                    # Removes files that have already been added
                    for i, j in enumerate(temp_fileNames):
                        for o, k in enumerate(non_existing_files):
                            if j == k: 
                                non_existing_files_index.append(i)
                                new_files = [files[item] for item in non_existing_files_index]
                                break
                elif buttonReply == QMessageBox.YesToAll:
                    # Removes files that have already been added
                    for i, j in enumerate(temp_fileNames):
                        for o, k in enumerate(non_existing_files):
                            if j == k: non_existing_files_index.append(i)
                    new_files = [files[item] for item in non_existing_files_index]
                    break
            new_files = list(dict.fromkeys(new_files))
            if not existing_files: 
                self.start_conversion(files)
                return
            if new_files: self.start_conversion(new_files)
            else: QMessageBox.information(self, 'All files already exist.', f"All the selected files are already added.\nThere are no new files to add.", QMessageBox.Ok, QMessageBox.Ok)
    def openImage(self, path):
        # threading.Thread(target=self.startThreadOpenImage,args=(path,)).start()
        # def startThreadOpenImage(self, path):
        self.getSize()
        self.vi = view_image(path)
        self.vi.show()
        self.close()
    def openAbout(self):
        self.about = aboutwindowUI()
        self.about.show()
    def delete(self, path):
        for o, k in enumerate(image_locations):
            if k == path:
                if os.path.exists(k): os.remove(k)
                Data_JSON_Contents.pop(o)
                sortedList = sorted(Data_JSON_Contents, key = lambda i: i['fileName'])
                with open(Data_JSON, mode='w+', encoding='utf-8') as file: json.dump(sortedList, file, ensure_ascii=True, indent=4, sort_keys=True)
        self.clearLayout(self.gridLayoutItems)
        self.reloadListUI('')
    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None: widget.deleteLater()
                else: self.clearLayout(item.layout())
    def print_widget(self, printer):
        screen = self.grab()
        image = QImage(screen)
        # painter = QPainter(image)
        image.save("capture.png")

        # painter.end()
        self.openImage('capture.png')
    def reloadListUI(self, searchText):
        load_data_file(file_names, image_locations, quantities)
        self.txtBoxList.clear()
        if searchText == '':
            for i, j in enumerate(file_names):
                label = QLabel(j)
                label.setObjectName('Name')
                # label.setFixedSize(128,20)
                self.gridLayoutItems.addWidget(label, i, 0)
                
                textBoxInput = QLineEdit("1")
                textBoxInput.setObjectName('Quantity')
                textBoxInput.setAlignment(QtCore.Qt.AlignCenter)
                textBoxInput.setValidator(QIntValidator())
                textBoxInput.setText(str(quantities[i]))
                textBoxInput.editingFinished.connect(partial(self.saveLineEdit, textBoxInput, i))
                textBoxInput.setFocusPolicy(Qt.StrongFocus)
                self.txtBoxList.append(textBoxInput)
                textBoxInput.setFixedSize(70,50)
                self.gridLayoutItems.addWidget(textBoxInput, i, 1)
                
                btnImage = QPushButton()
                btnImage.clicked.connect(partial(self.openImage, image_locations[i]))
                btnImage.setIcon(QIcon(image_locations[i]))
                btnImage.setIconSize(QSize(512,100))
                btnImage.setFixedSize(512,100)
                btnImage.setFlat(True)
                self.gridLayoutItems.addWidget(btnImage, i, 2)
                
                btnDelete = QPushButton()
                btnDelete.setFlat(True)
                btnDelete.setFixedSize(32,32)
                btnDelete.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogDiscardButton')))
                btnDelete.clicked.connect(partial(self.delete, image_locations[i]))
                self.gridLayoutItems.addWidget(btnDelete, i, 3)
        else:
            for i, j in enumerate(file_names):
                if searchText.lower() in j.lower():
                    label = QLabel(j)
                    label.setObjectName('Name')
                    # label.setFixedSize(128,20)
                    self.gridLayoutItems.addWidget(label, i, 0)
                    
                    textBoxInput = QLineEdit("1")
                    textBoxInput.setObjectName('Quantity')
                    textBoxInput.setAlignment(QtCore.Qt.AlignCenter)
                    textBoxInput.setValidator(QIntValidator())
                    textBoxInput.setText(str(quantities[i]))
                    textBoxInput.editingFinished.connect(partial(self.saveLineEdit, textBoxInput, i))
                    textBoxInput.setFocusPolicy(Qt.StrongFocus)
                    self.txtBoxList.append(textBoxInput)
                    textBoxInput.setFixedSize(70,50)
                    self.gridLayoutItems.addWidget(textBoxInput, i, 1)
                    
                    btnImage = QPushButton()
                    btnImage.clicked.connect(partial(self.openImage, image_locations[i]))
                    btnImage.setIcon(QIcon(image_locations[i]))
                    btnImage.setIconSize(QSize(512,100))
                    btnImage.setFixedSize(512,100)
                    btnImage.setFlat(True)
                    self.gridLayoutItems.addWidget(btnImage, i, 2)
                    
                    btnDelete = QPushButton()
                    btnDelete.setFlat(True)
                    btnDelete.setFixedSize(32,32)
                    btnDelete.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogDiscardButton')))
                    btnDelete.clicked.connect(partial(self.delete, image_locations[i]))
                    self.gridLayoutItems.addWidget(btnDelete, i, 3)
        if not self.txtBoxList:
            label = QLabel()
            if not file_names: 
                label.setText(f'<br>Drag files here to add them to the program\n<br><a href=\"https://\">Or Choose your files</a>')
                clickableLabel(label).connect(partial(self.add, True, ''))
            else: label.setText(f'Could not find a file named: "{searchText}"')
            label.setObjectName('Name')
            # label.setOpenExternalLinks(True)
            # label.linkActivated.connect(partial(self.add, True, ''))
            label.setAlignment(QtCore.Qt.AlignCenter)
            # label.setFixedSize(128,20)
            self.gridLayoutItems.addWidget(label, 0, 0)
        
        time.sleep(0.5)
        # if self.txtBoxList: self.txtBoxList[self.lastTextBoxInFucos].setFocus()
        
        # print(self.lastTextBoxInFucos)
        # self.gridLayoutItems.setColumnStretch(3,0)
    def saveLineEdit(self, textBox, index):
        self.newQuantity = textBox.text()
        if '.' in self.newQuantity:
            QMessageBox.critical(self, 'Must be an integer.', "Must be a whole number.\n\nNo decimal places", QMessageBox.Ok, QMessageBox.Ok)
            return
        elif self.newQuantity == '': return
        elif self.newQuantity == quantities[index]: return
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
        self.reloadListUI(self.txtSearch.text())
    def search(self):
        text = self.txtSearch.text()
        self.clearLayout(self.gridLayoutItems)
        self.reloadListUI(text)
    def save(self):
        print("saved")
        Data_JSON_Contents.clear()
        for i, j in enumerate(file_names):
            num = quantities[i]
            path = image_locations[i]
            Data_JSON_Contents.append({
            'fileName': [j],
            'imgLoc': [path],
            'quantity':[int(num)]
            })
        sortedList = sorted(Data_JSON_Contents, key = lambda i: i['fileName'])
        with open(Data_JSON, mode='w+', encoding='utf-8') as file: json.dump(sortedList, file, ensure_ascii=True, indent=4, sort_keys=True)
class view_image(QMainWindow):
    def __init__(self, directory_to_open,):
        super(view_image, self).__init__()
        self.viewer = PhotoViewer(self)
        self.image_to_open = directory_to_open
        directory_to_open = directory_to_open.replace('\\','/')

        self.printer = QPrinter()
        self.setWindowTitle(directory_to_open)
        self.createActions()
        self.createMenus()
        # self.resize(width, height)

        screen = app.primaryScreen()
        rect = screen.availableGeometry()

        self.setGeometry(0, 0, rect.width(), rect.height())
        self.viewer.photoClicked.connect(self.photoClicked)

        # Arrange layout
        self.VBlayout = QVBoxLayout(self)
        self.VBlayout.addWidget(self.viewer)
        self.HBlayout = QHBoxLayout(self)
        self.HBlayout.setAlignment(Qt.AlignLeft)
        self.VBlayout.addLayout(self.HBlayout)
        self.setCentralWidget(self.viewer)
        self.loadImage() 
        self.viewer.fitInView(True)
        # self.setCentralWidget(VBlayout)
        # self.menuBar = QMenuBar(self)
    
    def createActions(self):
        self.printAct = QAction("&Print...", self, shortcut="Ctrl+P", enabled=True, triggered=self.print_)

    def createMenus(self):
        self.fileMenu = QMenu("&File", self)
        self.fileMenu.addAction(self.printAct)
        self.menuBar().addMenu(self.fileMenu)

    def print_(self):
        dialog = QtPrintSupport.QPrintPreviewDialog() # PyQt5
        # dialog = QPrintPreviewDialog()
        dialog.paintRequested.connect(self.handlePaintRequest)
        dialog.exec_()

    def handlePaintRequest(self, printer):
        self.viewer.render(QPainter(printer))
        
    def handlePrint(self):
        dialog = QtPrintSupport.QPrintDialog()
        if dialog.exec_() == QDialog.Accepted:
            self.editor.document().print_(dialog.printer())

        # dialog = QPrintDialog(self.printer, self)
        # if dialog.exec_():
        #     painter = QPainter(self.printer)
        #     rect = painter.viewport()
        #     size = self.imageLabel.pixmap().size()
        #     size.scale(rect.size(), Qt.KeepAspectRatio)
        #     painter.setViewport(rect.x(), rect.y(), size.width(), size.height())
        #     painter.setWindow(self.imageLabel.pixmap().rect())
        #     painter.drawPixmap(0, 0, self.imageLabel.pixmap())
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
class PhotoViewer(QGraphicsView):
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
        # self.setBackgroundBrush(QBrush(QColor(30, 30, 30)))
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
class aboutwindowUI(QDialog):
    def __init__(self, parent=None):
        super(aboutwindowUI, self).__init__(parent)
        uic.loadUi('JordanProgramListOrginizer/aboutwindow.ui', self)
        self.setWindowTitle("About")
        self.setWindowIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogInfoView')))
        self.icon = self.findChild(QLabel, 'lblIcon')
        self.icon.setFixedSize(128,128)
        pixmap = QPixmap('icon.png')
        myScaledPixmap = pixmap.scaled(self.icon.size(), Qt.KeepAspectRatio)
        self.icon.setPixmap(myScaledPixmap)
        self.lisenceText = self.findChild(QLabel,'label_2')
        with open('LICENSE.md', 'r') as f: self.lisenceText.setText(f.read())
        self.btnClose = self.findChild(QPushButton, 'btnClose')
        self.btnClose.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogCloseButton')))
        self.btnClose.clicked.connect(self.close)
        self.resize(750,450)
        self.show()
def clickableLabel(widget):
    class Filter(QObject):
        clicked = pyqtSignal()
        def eventFilter(self, obj, event):
            if obj == widget:
                if event.type() == QEvent.MouseButtonRelease:
                    if obj.rect().contains(event.pos()):
                        self.clicked.emit()
                        # The developer can opt for .emit(obj) to get the object within the slot.
                        return True
            return False
    filter = Filter(widget)
    widget.installEventFilter(filter)
    return filter.clicked
def load_data_file(*args):
    global Data_JSON_Contents
    for i, j in enumerate(args): j.clear()
    with open(Data_JSON) as file:
        Data_JSON_Contents = json.load(file)
        for info in Data_JSON_Contents:
            for name in info['fileName']: file_names.append(name)
            for path in info['imgLoc']: image_locations.append(path)
            for quan in info['quantity']: quantities.append(quan)
if __name__ == '__main__':
    # if images directory doesnt exist we create it
    if not os.path.exists('Images'): os.makedirs('Images')
    # if data.json file doesn't exist, we create it
    if not os.path.isfile(Data_JSON): 
        with open(Data_JSON, 'w+') as f: f.write("[]")
    # Load data file
    load_data_file(file_names, image_locations, quantities)
    # start GUI
    app = QApplication(sys.argv)
    window = mainwindowUI()
    sys.exit(app.exec_())
