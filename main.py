import json
import os
import sys
from functools import partial

import cv2
import ezdxf
import ctypes
import imutils
import threading
import subprocess
import matplotlib.pyplot as plt
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from PyQt5 import *
from PyQt5 import QtCore, QtGui, QtPrintSupport, QtWidgets, uic
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from PyQt5.QtWidgets import *

Data_JSON = "data.json"
Data_JSON_Contents = []

file_names = []
image_locations = []
quantities = []
description = []
window_geometry = [100, 200, 1000, 600]

company = 'TheCodingJs'
title = 'DXF to PNG'
version = 'v1.0.3'


class ConvertThread(QThread):
    data_downloaded = pyqtSignal(object)

    def __init__(self, file):
        QThread.__init__(self)
        self.file = file
        self.default_img_format = '.png'
        self.default_img_res = 300

    def run(self):
        self.data_downloaded.emit(f'1/{len(self.file)} - Starting.')
        loop = QEventLoop()
        QTimer.singleShot(1000, loop.quit)
        loop.exec_()
        for i, j in enumerate(self.file):
            dxffilepath = j
            # Generate file name
            temp_fileName = j.split("/")[-1].split(".")[0]

            # Gnerate save file Location
            path = os.path.dirname(os.path.abspath(__file__)) + '/Images/' + temp_fileName + '.png'.replace('\\', '/')
            path = path.split('/')
            path[0] = path[0].capitalize()
            path = '/'.join(path)

            self.data_downloaded.emit(f'{i+1}/{len(self.file)} - {temp_fileName} - Converting..')
            self.convert_dxf2img(temp_fileName, dxffilepath, path, img_format='.png', img_res = 300, index=i)

            Data_JSON_Contents.append({
                'fileName': [temp_fileName],
                'imgLoc': ['/Images/' + temp_fileName + '.png'],
                'quantity': [1],
                'description': ['']
            })
            with open(Data_JSON, mode='w+', encoding='utf-8') as file:
                sortedList = sorted(Data_JSON_Contents, key = lambda i: i['fileName'])
                json.dump(sortedList, file, ensure_ascii=True, indent=4, sort_keys=True)
        self.data_downloaded.emit('Finished!')
    def convert_dxf2img(self, name, path, save_to, img_format, img_res, index):
        # for name in names:
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        # Recommended: audit & repair DXF document before rendering
        auditor = doc.audit()
        # The auditor.errors attribute stores severe errors,
        # which *may* raise exceptions when rendering.
        if len(auditor.errors) != 0:
            self.data_downloaded.emit(f'{index+1}/{len(self.file)} - {name} - Error!')
            loop = QEventLoop()
            QTimer.singleShot(1000, loop.quit)
            loop.exec_()
            return
        else :
            fig = plt.figure()
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            ctx.set_current_layout(msp)
            ctx.current_layout.set_colors(bg='#FFFFFF')
            out = MatplotlibBackend(ax)
            Frontend(ctx, out).draw_layout(msp, finalize=True)
            self.data_downloaded.emit(f'{index+1}/{len(self.file)} - {name} - Saving...')
            fig.savefig(save_to, dpi=img_res)
            im = cv2.imread(save_to)
            hei, wid, c = im.shape
            if hei > wid:
                region = imutils.rotate_bound(im, 90)
                cv2.imwrite(save_to, region)
            plt.close(fig)

class mainwindowUI(QMainWindow):
    resized = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(mainwindowUI, self).__init__(parent)
        uic.loadUi('UI/mainwindow.ui', self)
        if 'linux' not in sys.platform:
            appid = u'{}.{}.{}'.format(company, title, version)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(appid)


        self.setWindowIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/icon.png"))
        self.setWindowTitle(f'{title} - {version}')
        self.printer = QPrinter()

        self.returns = {}

        self.setAcceptDrops(True)
        self.setGeometry(window_geometry[0], window_geometry[1], window_geometry[2], window_geometry[3])
        self.resized.connect(self.getSize)

        self.txtBoxList = []
        self.lastTextBoxInFucos = 0
        self.setStyleSheet(open("style.qss", "r").read())

        self.Hline = self.findChild(QLine, 'Hline')
        
        self.btnAdd = self.findChild(QPushButton, 'btnAdd')
        self.btnAdd.setObjectName('btnAdd')
        self.btnAdd.clicked.connect(partial(self.add, True, ''))
        self.btnAdd.setShortcut('Ctrl+O')

        # saveShortcut = QShortcut(QKeySequence("Ctrl+s"), self)
        # saveShortcut.activated.connect(self.save)

        self.txtSearch = self.findChild(QLineEdit, 'txtSearch')
        self.txtSearch.editingFinished.connect(self.search)

        self.lblState = self.findChild(QLabel, 'lblState')
        self.lblState.setHidden(True)

        self.progressBar = self.findChild(QProgressBar, 'progressBar')
        self.progressBar.setHidden(True)
        self.progressBar.setAlignment(QtCore.Qt.AlignLeft)

        self.actionPrint = self.findChild(QAction, 'actionPrint')
        self.actionPrint.triggered.connect(self.print_widget)
        self.actionPrint.setShortcut('Ctrl+P')

        self.PrintWidget = self.findChild(QGroupBox, 'PrintWidget')

        self.actionAbout = self.findChild(QAction, 'actionAbout_2')
        self.actionAbout.triggered.connect(self.openAbout)
        self.actionAbout.setIcon(QIcon(os.path.dirname(os.path.realpath(__file__)) + "/icon.png"))
        # self.actionAbout.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogInfoView')))

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

        # threading.Thread(target=self.startThreadOpenImage,args=(path,)).start()
        # threading.Thread(target=self.reloadListUI, args=(self.gridLayoutItems, '',)).start()
        self.reloadListUI('')

        # self.print_widget()

        self.show()
        self.center()

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
            links = [str(url.toLocalFile()) for url in event.mimeData().urls()]
            self.add(False, links)
        else: event.ignore()

    def start_conversion(self, files):
        self.setCursor(Qt.BusyCursor)
        self.threads = []
        converter = ConvertThread(files)
        converter.data_downloaded.connect(self.on_data_ready)
        self.threads.append(converter)
        converter.start()

    def on_data_ready(self, text):
        # self.lblState.setHidden(False)
        self.progressBar.setHidden(False)
        self.lblState.setText(f"{text}")
        if text not in ['Finished!', '']:
            currentNum = text.split('/')
            currentNum = int(currentNum[0])

            maxnum = text.split('/')
            maxnum = maxnum[1]
            maxnum = maxnum.split(' - ')
            maxnum = int(maxnum[0])

            self.progressBar.setValue(currentNum)
            self.progressBar.setMaximum(maxnum)
        self.progressBar.setFormat(' ' + text)
        if text in ['', 'Finished!']:
            self.clearLayout(self.gridLayoutItems)
            self.reloadListUI('')
            self.progressBar.setHidden(True)
            self.unsetCursor()

    def add(self, openFileDirectory, dragDropFiles):
        # open file directory
        if openFileDirectory: files, _ = QFileDialog.getOpenFileNames(self, "Add Files", "", "DXF Files (*.dxf)")
        else: files = dragDropFiles
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
            # Generate file name
            for i, j in enumerate(files): temp_fileNames.append(j.split("/")[-1].split(".")[0])
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

    def btnOpenPath(self, path):
        FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
        path = os.path.normpath(path)
        if os.path.isdir(path): subprocess.run([FILEBROWSER_PATH, path], stdout=subprocess.PIPE, stderr=sbuprocess.PIPE, stdin=subprocess.PIPE)
        elif os.path.isfile(path): subprocess.run([FILEBROWSER_PATH, '/select,', os.path.normpath(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

    def openImage(self, path):
        self.getSize()
        self.vi = QImageViewer(path)
        self.vi.show()
        # self.close()

    def openAbout(self):
        self.about = aboutwindowUI()
        self.about.show()

    def delete(self, path):
        for o, k in enumerate(image_locations):
            if k == path:
                if os.path.exists(k): os.remove(k)
                Data_JSON_Contents.pop(o)
                sortedList = sorted(Data_JSON_Contents, key=lambda i: i['fileName'])
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
        screen = self.PrintWidget.grab()
        image = QImage(screen)
        image.save("capture.png")
        self.openImage('capture.png')

    def reloadListUI(self, searchText):
        self.setCursor(Qt.BusyCursor)
        load_data_file(file_names, image_locations, quantities, description)
        self.txtBoxList.clear()
        for i, j in enumerate(file_names):
            if (searchText != ''and searchText.lower() in j.lower() or searchText == ''):
                self.label = QPushButton(j)
                self.label.clicked.connect(partial(self.btnOpenPath, os.path.dirname(os.path.abspath(__file__)) + image_locations[i]))
                self.label.setObjectName('Name')
                self.label.setStyleSheet('text-align: left;')
                self.label.setToolTip(f'Opens {j} in file explorer.')
                self.label.setFont(QFont('Arial', 14))
                self.label.setFlat(True)

                self.textBoxInput = QLineEdit("1")
                self.textBoxInput.setObjectName('Quantity')
                self.textBoxInput.setAlignment(QtCore.Qt.AlignCenter)
                self.textBoxInput.setValidator(QIntValidator())
                self.textBoxInput.setText(str(quantities[i]))
                self.textBoxInput.editingFinished.connect(partial(self.saveLineEdit, self.textBoxInput, i, True))
                self.textBoxInput.setFocusPolicy(Qt.StrongFocus)
                self.textBoxInput.setFixedSize(60, 40)
                self.txtBoxList.append(self.textBoxInput)

                self.textBoxDescription = TextEdit(self)
                self.textBoxDescription.setAlignment(QtCore.Qt.AlignCenter)
                self.textBoxDescription.setText(str(description[i]))
                self.textBoxDescription.editingFinished.connect(
                    partial(self.saveLineEdit, self.textBoxDescription, i, False))
                self.textBoxDescription.setFocusPolicy(Qt.StrongFocus)
                self.textBoxDescription.setPlaceholderText('Enter notes here...')
                self.textBoxDescription.setFixedSize(100, 70)

                self.btnImage = QPushButton()
                self.btnImage.setObjectName('btnImage')
                self.btnImage.clicked.connect(partial(self.openImage, os.path.dirname(os.path.abspath(__file__)) + image_locations[i]))
                self.btnImage.setIcon(QIcon(os.path.dirname(os.path.abspath(__file__)) + image_locations[i]))
                self.btnImage.setIconSize(QSize(300-6, 100-6))
                self.btnImage.setFixedSize(300, 100)
                self.btnImage.setFlat(True)
                self.btnImage.setToolTip(os.path.dirname(os.path.abspath(__file__)) + image_locations[i])

                self.btnDelete = QPushButton()
                self.btnDelete.setFlat(True)
                self.btnDelete.setToolTip('Will delete: ' + os.path.dirname(os.path.abspath(__file__)) + image_locations[i] + ' and all of the saved data.')
                self.btnDelete.setFixedSize(32, 32)
                self.btnDelete.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogDiscardButton')))
                self.btnDelete.clicked.connect(partial(self.delete, image_locations[i]))
                # for k in range(5):
                self.gridLayoutItems.addWidget(QHLine(), i + i + 1,0)
                self.gridLayoutItems.addWidget(QHLine(), i + i + 1,1)
                self.gridLayoutItems.addWidget(QHLine(), i + i + 1,2)
                self.gridLayoutItems.addWidget(QHLine(), i + i + 1,3)
                self.gridLayoutItems.addWidget(QHLine(), i + i + 1,4)
                self.gridLayoutItems.addWidget(QHLine(), i + i + 1,5)
                self.lbl = QLabel('Name:')
                self.lbl.setFixedWidth(140)
                self.GridLayoutHeaders.addWidget(self.lbl, 0,0)
                self.lbl = QLabel('Notes:')
                self.lbl.setFixedWidth(60)
                self.GridLayoutHeaders.addWidget(self.lbl, 0,1)
                self.lbl = QLabel('Quantity:')
                self.lbl.setFixedWidth(60)
                self.GridLayoutHeaders.addWidget(self.lbl, 0,2)
                self.lbl = QLabel('Image:')
                self.lbl.setFixedWidth(300)
                self.GridLayoutHeaders.addWidget(self.lbl, 0,3)
                # self.gridLayoutItems.addWidget(QVLine(), i,0)
                # self.gridLayoutItems.addWidget(QVLine(), i,1)
                # self.gridLayoutItems.addWidget(QVLine(), i,2,Qt.AlignLeft)
                # self.gridLayoutItems.addWidget(QVLine(), i,3)
                # self.gridLayoutItems.addWidget(QVLine(), i,4)
                # self.gridLayoutItems.addWidget(QVLine(), i,5)
                # self.gridLayoutItems.addWidget(QVLine(), i,6)
                
                self.gridLayoutItems.addWidget(self.label, i + i + 2, 0, Qt.AlignCenter)
                self.gridLayoutItems.addWidget(self.textBoxDescription, i + i + 2, 1, Qt.AlignCenter)
                self.gridLayoutItems.addWidget(self.textBoxInput, i + i + 2, 2, Qt.AlignCenter)
                self.gridLayoutItems.addWidget(self.btnImage, i + i + 2, 3, Qt.AlignCenter)
                self.gridLayoutItems.addWidget(self.btnDelete, i + i + 2, 4, Qt.AlignCenter)
                self.gridLayoutItems.addWidget(self.btnDelete, i + i + 2, 5, Qt.AlignRight)

                # loop = QEventLoop()
                # QTimer.singleShot(10, loop.quit)
                # loop.exec_()
                    # loop = QEventLoop()
                    # QTimer.singleShot(100, loop.quit)
                    # loop.exec_()
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


        self.unsetCursor()
        # time.sleep(0.5)
        # if self.txtBoxList: self.txtBoxList[self.lastTextBoxInFucos].setFocus()

        # print(self.lastTextBoxInFucos)
        # self.gridLayoutItems.setColumnStretch(3,0)

    def saveLineEdit(self, textBox, index, isInt):
        self.setCursor(Qt.BusyCursor)
        text = textBox.text() if isInt else textBox.toPlainText()
        t = threading.Thread(target=self.saveLineEditThreading,
                   args=('isdone', text, index, isInt,))
        t.start()
        t.join()
        if self.returns['isdone'] == 'True':
        #     self.lastTextBoxInFucos = index
        #     self.clearLayout(self.gridLayoutItems)
        #     self.reloadListUI(self.txtSearch.text())
            self.unsetCursor()

    def saveLineEditThreading(self, bar, text, index, isInt):
        load_data_file(file_names, image_locations, quantities, description)
        if isInt:
            self.newQuantity = text
            if '.' in self.newQuantity:
                QMessageBox.critical(self, 'Must be an integer.', "Must be a whole number.\n\nNo decimal places", QMessageBox.Ok, QMessageBox.Ok)
                return
            elif self.newQuantity in ['', quantities[index]]: return
            Data_JSON_Contents.pop(index)
            Data_JSON_Contents.append({
                'fileName': [file_names[index]],
                'imgLoc': [image_locations[index]],
                'quantity':[int(self.newQuantity)],
                'description': [description[index]]
            })
            sortedList = sorted(Data_JSON_Contents,
                                key=lambda i: i['fileName'])
            with open(Data_JSON, mode='w+', encoding='utf-8') as file:
                json.dump(sortedList, file, ensure_ascii=True,
                          indent=4, sort_keys=True)
        else:
            Data_JSON_Contents.pop(index)
            Data_JSON_Contents.append({
                'fileName': [file_names[index]],
                'imgLoc': [image_locations[index]],
                'quantity': [int(quantities[index])],
                'description': [text]
            })
        # save data to JSON file
            sortedList = sorted(Data_JSON_Contents, key=lambda i: i['fileName'])
            with open(Data_JSON, mode='w+', encoding='utf-8') as file: json.dump(sortedList, file, ensure_ascii=True, indent=4, sort_keys=True)
        self.returns[bar] = 'True'
    def search(self):
        text = self.txtSearch.text()
        self.clearLayout(self.gridLayoutItems)
        self.reloadListUI(text)

    def save(self):
        self.setCursor(Qt.BusyCursor)
        Data_JSON_Contents.clear()
        for i, j in enumerate(file_names):
            Data_JSON_Contents.append({
                'fileName': [j],
                'imgLoc': [image_locations[i]],
                'quantity': [int(quantities[i])],
                'description': [description[i]]
            })
        sortedList = sorted(Data_JSON_Contents, key=lambda i: i['fileName'])
        with open(Data_JSON, mode='w+', encoding='utf-8') as file: json.dump(sortedList, file, ensure_ascii=True, indent=4, sort_keys=True)
        self.unsetCursor()

    def center(self):
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())

class TextEdit(QTextEdit):
    """
    A TextEdit editor that sends editingFinished events
    when the text was changed and focus is lost.
    """

    editingFinished = QtCore.pyqtSignal()
    receivedFocus = QtCore.pyqtSignal()

    def __init__(self, parent):
        super(TextEdit, self).__init__(parent)
        self._changed = False
        self.setTabChangesFocus( True )
        self.textChanged.connect( self._handle_text_changed )

    def focusInEvent(self, event):
        super(TextEdit, self).focusInEvent( event )
        self.receivedFocus.emit()

    def focusOutEvent(self, event):
        if self._changed:
            self.editingFinished.emit()
        super(TextEdit, self).focusOutEvent( event )

    def _handle_text_changed(self):
        self._changed = True

    def setTextChanged(self, state=True):
        self._changed = state

    def setHtml(self, html):
        QtGui.QTextEdit.setHtml(self, html)
        self._changed = False


class QImageViewer(QMainWindow):
    def __init__(self, directory_to_open):
        super().__init__()

        self.path = directory_to_open
        
        self.printer = QPrinter()
        self.scaleFactor = 0.0

        self.imageLabel = QLabel()
        self.imageLabel.setBackgroundRole(QPalette.Base)
        self.imageLabel.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.imageLabel.setScaledContents(True)

        self.scrollArea = QScrollArea()
        self.scrollArea.setBackgroundRole(QPalette.Dark)
        self.scrollArea.setWidget(self.imageLabel)
        self.scrollArea.setVisible(False)

        self.setCentralWidget(self.scrollArea)

        self.createActions()
        self.createMenus()

        self.setWindowTitle("Image Viewer")
        self.resize(800, 600)

        pixmap = QPixmap(self.path)
        # pixmap = pixmap.scaled(pixmap.height(), pixmap.height(), Qt.KeepAspectRatio, Qt.FastTransformation)
        self.imageLabel.setPixmap(pixmap)
        self.imageLabel.adjustSize()
        self.scaleFactor = 1.0

        self.scrollArea.setVisible(True)
        self.printAct.setEnabled(True)
        self.fitToWindowAct.setEnabled(True)
        self.updateActions()

        if not self.fitToWindowAct.isChecked():
            self.imageLabel.adjustSize()

    def print_(self):
        dialog = QPrintDialog(self.printer, self)
        if dialog.exec_():
            painter = QPainter(self.printer)
            rect = painter.viewport()
            size = self.imageLabel.pixmap().size()
            size.scale(rect.size(), Qt.KeepAspectRatio)
            painter.setViewport(rect.x(), rect.y(),
                                size.width(), size.height())
            painter.setWindow(self.imageLabel.pixmap().rect())
            painter.drawPixmap(0, 0, self.imageLabel.pixmap())

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.scaleFactor = 1.0

    def fitToWindow(self):
        fitToWindow = self.fitToWindowAct.isChecked()
        self.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()

        self.updateActions()

    def about(self):
        QMessageBox.about(self, "About Image Viewer",
                          "<p>The <b>Image Viewer</b> example shows how to combine "
                          "QLabel and QScrollArea to display an image. QLabel is "
                          "typically used for displaying text, but it can also display "
                          "an image. QScrollArea provides a scrolling view around "
                          "another widget. If the child widget exceeds the size of the "
                          "frame, QScrollArea automatically provides scroll bars.</p>"
                          "<p>The example demonstrates how QLabel's ability to scale "
                          "its contents (QLabel.scaledContents), and QScrollArea's "
                          "ability to automatically resize its contents "
                          "(QScrollArea.widgetResizable), can be used to implement "
                          "zooming and scaling features.</p>"
                          "<p>In addition the example shows how to use QPainter to "
                          "print an image.</p>")

    def createActions(self):
        # self.openAct = QAction(
        #     "&Open...", self, shortcut="Ctrl+O", triggered=self.open)
        self.printAct = QAction(
            "&Print...", self, shortcut="Ctrl+P", enabled=False, triggered=self.print_)
        self.exitAct = QAction(
            "E&xit", self, shortcut="Ctrl+Q", triggered=self.close)
        self.zoomInAct = QAction(
            "Zoom &In (25%)", self, shortcut="Ctrl++", enabled=False, triggered=self.zoomIn)
        self.zoomOutAct = QAction(
            "Zoom &Out (25%)", self, shortcut="Ctrl+-", enabled=False, triggered=self.zoomOut)
        self.normalSizeAct = QAction(
            "&Normal Size", self, shortcut="Ctrl+S", enabled=False, triggered=self.normalSize)
        self.fitToWindowAct = QAction("&Fit to Window", self, enabled=False, checkable=True, shortcut="Ctrl+F",
                                      triggered=self.fitToWindow)
        self.aboutAct = QAction("&About", self, triggered=self.about)
        self.aboutQtAct = QAction("About &Qt", self, triggered=qApp.aboutQt)

    def createMenus(self):
        self.fileMenu = QMenu("&File", self)
        # self.fileMenu.addAction(self.openAct)
        self.fileMenu.addAction(self.printAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.viewMenu = QMenu("&View", self)
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.normalSizeAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.fitToWindowAct)

        self.helpMenu = QMenu("&Help", self)
        self.helpMenu.addAction(self.aboutAct)
        self.helpMenu.addAction(self.aboutQtAct)

        self.menuBar().addMenu(self.fileMenu)
        self.menuBar().addMenu(self.viewMenu)
        self.menuBar().addMenu(self.helpMenu)

    def updateActions(self):
        self.zoomInAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.zoomOutAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.normalSizeAct.setEnabled(not self.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        self.scaleFactor *= factor
        self.imageLabel.resize(self.scaleFactor * self.imageLabel.pixmap().size())

        self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

        self.zoomInAct.setEnabled(self.scaleFactor < 3.0)
        self.zoomOutAct.setEnabled(self.scaleFactor > 0.333)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                               + ((factor - 1) * scrollBar.pageStep() / 2)))

class view_image(QMainWindow):

    def __init__(self, directory_to_open,):
        super(view_image, self).__init__()
        self.viewer = PhotoViewer(self)
        self.image_to_open = directory_to_open
        directory_to_open = directory_to_open.replace('\\', '/')

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
        dialog = QtPrintSupport.QPrintPreviewDialog()  # PyQt5
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
        if self.viewer.dragMode() == QGraphicsView.NoDrag:
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

    def hasPhoto(self): return not self._empty

    def fitInView(self, scale=True):
        rect = QRectF(self._photo.pixmap().rect())
        if not rect.isNull():
            self.setSceneRect(rect)
            if self.hasPhoto():
                unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
                self.scale(1 / unity.width(), 1 / unity.height())
                viewrect = self.viewport().rect()
                scenerect = self.transform().mapRect(rect)
                factor = min(viewrect.width() / scenerect.width(), viewrect.height() / scenerect.height())
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
            if self._zoom > 0: self.scale(factor, factor)
            elif self._zoom == 0: self.fitInView()
            else: self._zoom = 0

    def toggleDragMode(self):
        if self.dragMode() == QGraphicsView.ScrollHandDrag: self.setDragMode(QGraphicsView.NoDrag)
        elif not self._photo.pixmap().isNull(): self.setDragMode(QGraphicsView.ScrollHandDrag)

    def mousePressEvent(self, event):
        if self._photo.isUnderMouse(): self.photoClicked.emit(self.mapToScene(event.pos()).toPoint())
        super(PhotoViewer, self).mousePressEvent(event)


class aboutwindowUI(QDialog):

    def __init__(self, parent=None):
        super(aboutwindowUI, self).__init__(parent)
        uic.loadUi('UI/aboutwindow.ui', self)
        self.setWindowTitle("About")
        self.setWindowIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogInfoView')))
        self.icon = self.findChild(QLabel, 'lblIcon')
        self.icon.setFixedSize(128, 128)
        pixmap = QPixmap('icon.png')
        myScaledPixmap = pixmap.scaled(self.icon.size(), Qt.KeepAspectRatio)
        self.icon.setPixmap(myScaledPixmap)
        self.lisenceText = self.findChild(QLabel, 'label_2')
        with open('LICENSE', 'r') as f:
            self.lisenceText.setText(f.read())
        self.btnClose = self.findChild(QPushButton, 'btnClose')
        self.btnClose.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogCloseButton')))
        self.btnClose.clicked.connect(self.close)
        self.resize(750, 450)
        self.show()

class QHLine(QFrame):
    def __init__(self):
        super(QHLine, self).__init__()
        self.setFrameShape(QFrame.HLine)
        self.setFrameShadow(QFrame.Sunken)


class QVLine(QFrame):
    def __init__(self):
        super(QVLine, self).__init__()
        self.setFrameShape(QFrame.VLine)
        self.setFrameShadow(QFrame.Sunken)
        # self.setFixedWidth(10)
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
            for disc in info['description']:
                description.append(disc)


if __name__ == '__main__':
    # if images directory doesn't exist we create it
    if not os.path.exists('Images'): os.makedirs('Images')
    # if data.json file doesn't exist, we create it
    if not os.path.isfile(Data_JSON):
        with open(Data_JSON, 'w+') as f: f.write("[]")
    # Load data file
    load_data_file(file_names, image_locations, quantities, description)
    # start GUI
    app = QApplication(sys.argv)
    window = mainwindowUI()
    sys.exit(app.exec_())
