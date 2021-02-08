import os
import sys
import cv2
import json
import ezdxf
import shutil
import ctypes
import imutils
import threading
import threading
import subprocess
from zipfile import ZipFile 
import zipfile
import matplotlib.pyplot as plt
from PyQt5 import *
from PIL import Image
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from functools import partial
from datetime import datetime
from natsort import natsort_keygen
from PyQt5.QtPrintSupport import QPrintDialog, QPrinter
from ezdxf.addons.drawing import Frontend, RenderContext
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from PyQt5 import QtCore, QtGui, uic
import argparse

natsort_key = natsort_keygen()


SETTINGS_FILE = 'settings.txt'

try:
    file = open(SETTINGS_FILE, 'r')
except FileNotFoundError:
    with open(SETTINGS_FILE, 'w') as file:
        file.write('Batch.json')
with open(SETTINGS_FILE, 'r') as f:
    Data_JSON = 'Batches/' + f.read()

Data_JSON_Contents = []


BATCHES = []
NON_BATCHES = ['NON_BATCH']

file_names = []
image_locations = []
quantities = []
description = []
checkmarked = []
materials = []
batch_name_list = []
batch_index_val = []

batch_group_box_GUI = []

company = 'TheCodingJs'
title = 'DXF to PNG'
version = 'v1.0.3'

latest_update_date = datetime(2020, 11, 27, 2, 21, 6)
latest_update_date_formated = latest_update_date.strftime(
    "%A %B %d %Y at %X%p")


class ConvertThread(QThread):
    data_downloaded = pyqtSignal(object)

    def __init__(self, file, batch_name):
        QThread.__init__(self)
        self.file = file
        self.selected_batch_name = batch_name
        self.default_img_format = '.png'
        self.default_img_res = 300

    def run(self):
        print(self.file)
        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
        for i, j in enumerate(self.file):
            dxffilepath = j
            file_name, file_extension = os.path.splitext(j)
            file_name = file_name.replace('.','-')
            temp_fileName = file_name.split("/")[-1].split(".")[0]
            print(temp_fileName)
            path = os.path.dirname(os.path.abspath(
                __file__)) + '/Images/' + temp_fileName + '.png'.replace('\\', '/')
            path = path.split('/')
            path[0] = path[0].capitalize()
            path = '/'.join(path)
            print(path)
            clear_batches()
            load_batch(file_names, image_locations, quantities, description, checkmarked,
                       materials, batch_name_list, batch_index_val, BATCH=self.selected_batch_name)
            if file_extension.lower() == '.dxf':
                # ! make sure this works.
                if not os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + '/Images/' + temp_fileName + '.png'):
                    self.data_downloaded.emit(
                        f'{i+1}/{len(self.file)} - {temp_fileName} - Converting..')
                    self.convert_dxf2img(
                        temp_fileName, dxffilepath, path, img_format='.png', img_res=300, index=i)
                else:
                    self.data_downloaded.emit(
                        f'{i+1}/{len(self.file)} - {temp_fileName} - Saving..')
                Data_JSON_Contents[0][self.selected_batch_name].append({
                    'fileName': [temp_fileName],
                    'imgLoc': ['/Images/' + temp_fileName + '.png'],
                    'quantity': [1],
                    'description': [''],
                    'checked': ['False'],
                    'material': ['1/2 50W STEEL']
                })
            elif file_extension.lower() in ['.png', '.jpg', '.jpeg']:
                if not os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + '/Images/' + temp_fileName + file_extension.lower()):
                    self.data_downloaded.emit(
                        f'{i+1}/{len(self.file)} - {temp_fileName} - Copying..')
                    shutil.copyfile(dxffilepath, os.path.dirname(os.path.realpath(
                        __file__)) + '/Images/' + temp_fileName + file_extension.lower())
                else:
                    self.data_downloaded.emit(
                        f'{i+1}/{len(self.file)} - {temp_fileName} - Saving..')
                Data_JSON_Contents[0][self.selected_batch_name].append({
                    'fileName': [temp_fileName],
                    'imgLoc': ['/Images/' + temp_fileName + file_extension.lower()],
                    'quantity': [1],
                    'description': [''],
                    'checked': ['False'],
                    'material': ['1/2 50W STEEL']
                })
            with open(Data_JSON, mode='w+', encoding='utf-8') as file:
                json.dump(Data_JSON_Contents, file,
                          ensure_ascii=True, sort_keys=True)

        sort_data(self.selected_batch_name)
        self.data_downloaded.emit('Finished!')

    def convert_dxf2img(self, name, path, save_to, img_format, img_res, index):
        doc = ezdxf.readfile(path)
        msp = doc.modelspace()
        auditor = doc.audit()
        if len(auditor.errors) != 0:
            self.data_downloaded.emit(
                f'{index+1}/{len(self.file)} - {name} - Error!')
            loop = QEventLoop()
            QTimer.singleShot(1000, loop.quit)
            loop.exec_()
            return
        else:
            fig = plt.figure()
            ax = fig.add_axes([0, 0, 1, 1])
            ctx = RenderContext(doc)
            ctx.set_current_layout(msp)
            ctx.current_layout.set_colors(bg='#FFFFFF')

            out = MatplotlibBackend(ax, params={"lineweight_scaling": 6})
            Frontend(ctx, out).draw_layout(msp, finalize=True)

            self.data_downloaded.emit(
                f'{index+1}/{len(self.file)} - {name} - Saving...')
            fig.savefig(save_to, dpi=img_res)
            im = cv2.imread(save_to)
            hei, wid, c = im.shape
            if hei > wid:
                region = imutils.rotate_bound(im, 90)
                cv2.imwrite(save_to, region)
            plt.close(fig)


class ProcessImagesThread(QThread):
    sig = pyqtSignal()

    def __init__(self, shipto):
        QThread.__init__(self)
        self.shipto = shipto

    def run(self):
        self.process_images_Thread()
        self.sig.emit()

    def process_images_Thread(self):
        onlyfiles = [os.path.join('Capture/', fn)
                     for fn in next(os.walk('Capture/'))[2]]
        sorted(onlyfiles, key=natsort_key)
        font = cv2.FONT_HERSHEY_SIMPLEX
        parts_per_page = 24
        savedir = 'Print/'
        frame_num = 1
        cover_page = True
        first_batch_only = True
        for _, image_path in enumerate(onlyfiles):
            img = Image.open(image_path)
            width, height = img.size
            w, h = (width, (66 * parts_per_page))
            for num_of_times, row_i in enumerate(range(0, height, h)):
                if first_batch_only:
                    if num_of_times == 0 and cover_page:
                        # row_i += 28 #!TOP
                        h -= 222  # !BOTTOM
                        cover_page = False
                    elif num_of_times == 1:
                        row_i -= 222  # !TOP
                        h += 146  # !BOTTOM
                    elif num_of_times == 2:
                        row_i -= 306  # !TOP
                        h -= 6  # !BOTTOM
                    elif num_of_times == 3:
                        row_i -= 314  # !TOP
                        # h -= 6 #!BOTTOM
                else:
                    if num_of_times == 0:
                        # row_i -= 28
                        h += 28
                    elif num_of_times == 1:
                        row_i += 20
                        h -= 32
                    elif num_of_times == 2:
                        row_i += 18
                        h -= 12
                crop = img.crop((0, row_i, 0 + w, row_i + h))
                save_to = os.path.join(savedir, "print_{:003}.png")
                crop.save(save_to.format(frame_num))
                frame_num += 1
            first_batch_only = False

        onlyfiles = [os.path.join('Print/', fn)
                     for fn in next(os.walk('Print/'))[2]]
        onlyfiles.sort(key=natsort_key)

        run_only_once = True
        for page, file in enumerate(onlyfiles):
            if run_only_once:
                img = cv2.imread(file)
                h, w, _ = img.shape
                im = Image.open(file)
                im_new = self.add_margin(
                    im, 100, 0, 50, 0, (255, 255, 255, 255))
                im_new.save(file, quality=95)
                Image1 = Image.open(file)
                Image1copy = Image1.copy()
                Image2 = Image.open('vendor.png')
                Image2copy = Image2.copy()
                Image1copy.paste(Image2copy, (0, 0))
                Image1copy.save(file)
                img = cv2.imread(file)
                h, w, _ = img.shape
                cv2.putText(img, f'Ship To: {self.shipto}',
                            (int(w/3), 30), font, 1, (30, 30, 30), 2)
                # cv2.putText(img, f'{shipto}',
                #             (int(w/4), 62), font, 1, (0, 0, 0), 2)
                cv2.imwrite(file, img)
                run_only_once = False
            img = cv2.imread(file)
            h, w, _ = img.shape
            im = Image.open(file)
            im_new = self.add_margin(im, 0, 0, 50, 0, (255, 255, 255, 255))
            im_new.save(file, quality=95)
            img = cv2.imread(file)
            h, w, _ = img.shape
            cv2.putText(img, f'Page {page+1} of {len(onlyfiles)}',
                        (int(w/2-60), h-20), font, 1, (30, 30, 30), 2)
            cv2.imwrite(file, img)

            src = cv2.imread(file, 1)
            tmp = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY)
            _, alpha = cv2.threshold(tmp, 0, 255, cv2.THRESH_BINARY)
            b, g, r = cv2.split(src)
            rgba = [b, g, r, alpha]
            dst = cv2.merge(rgba, 4)
            cv2.imwrite(file, dst)
        clear_folders(['Capture'])

    def add_margin(self, pil_img, top, right, bottom, left, color):
        width, height = pil_img.size
        new_width = width + right + left
        new_height = height + top + bottom
        result = Image.new(pil_img.mode, (new_width, new_height), color)
        result.paste(pil_img, (left, top))
        return result


class mainwindowUI(QMainWindow):
    resized = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(mainwindowUI, self).__init__(parent)
        uic.loadUi('UI/mainwindow.ui', self)
        if 'linux' not in sys.platform:
            appid = u'{}.{}.{}'.format(company, title, version)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                appid)

        self.setMinimumSize(930, 500)
        self.setWindowIcon(QIcon(os.path.dirname(
            os.path.realpath(__file__)) + "/icon.png"))
        self.title_json = Data_JSON.replace('Batches/','').replace('.json','')
        self.txtCurrentViewingBatch.setText(self.title_json)
        self.setWindowTitle(f'{title} - {version} - {self.title_json}')

        self.setAcceptDrops(True)
        self.resized.connect(self.getSize)

        self.load_var()
        self.load_ui()

    def load_var(self):
        self.lastTextBoxInFucos = 0
        self.returns = {}
        self.txtBoxList = []
        self.last_search_text = ''
        self.materials = ["Stainless Steel 7GA", "Galvanized Steel  6GA", "Galvanized Steel  8GA", "Galvanized Steel 10GA", "Galvanized Steel 12GA", "Galvanized Steel 14GA", "Galvanized Steel 16GA", "Galvanized Steel 18GA", "Galvanized Steel 20GA", "Galvanized Steel 22GA", "Galvanized Steel 24GA", "Galvanized Steel 26GA", "Stainless Steel  6GA", "Stainless Steel  8GA", "Stainless Steel 10GA", "Stainless Steel 12GA", "Stainless Steel 14GA", "Stainless Steel 16GA", "Stainless Steel 18GA", "Stainless Steel 20GA", "Stainless Steel 22GA", "Stainless Steel 24GA", "Stainless Steel 26GA", "Mild steel 18 Ga.", "Mild Steel 16 Ga.", "Mild Steel 14 Ga.", "Mild Steel 12 Ga.", "Mild Steel 10 Ga.", "Mild Steel 3/16", "Mild Steel 1/4", "Mild Steel 3/8", "Mild Steel 11 Ga.", "Mild Steel 5/16", "Mild Steel 3/4",
                          "Mild Steel 1/2", "Mild Steel 1", "CUSTOMER MATERIAL", "Mild Steel 5/8", "Stainless Steel 1/4", "BRASS 1/8", "Stainless Steel 3/8", "Mild Steel 7/8", "QT-100 3/16", "S.S. #4 Finish 12 GA.", "S.S. #4 Finish 14 GA.", "Mild Steel 22 Ga.", "S.S. #4 FINISH  16 GA.", "S.S. #4 FINISH  11 GA.", "3/16 ALUMINUM", "Mild Steel 8 Ga.", "3/4 AR 400", "5/8 AR400", "1/2 AR 400", "3/8 AR 400", "5/16 AR 400", "1/4 AR 400", "3/16 AR 400", "3/4 QT100", "5/8 QT100", "1/2 QT100", "3/8 QT100", "5/16 QT100", "1/4 QT100", "3/16 QT 100", "1/2 S.S.", "1/4 AR 200", "3/16 ALUM.", "18 GA STAINLESS/PVC COATING", "1/2 50W STEEL", "Mild Steel 20 GA.", "10GA. ALUMINUM", "1/4 ALUMINUM", "3/8 AR200", "ALUMINUM 16 GA", "ALUMINUM 1/8", "ALUMINUM 14 GA", "1/4 50W PLATE", "3/16 50W PLATE", "ROUND SOLID", "Mild Steel 10GA OR 11GA"]
        self.materials.sort()
        self.batches_to_load = []
        self.delete_buttons = []
        self.button_images = []
        self.images_path = []
        self.all_batch_checkboxes = {}
        self.all_batch_delete_buttons = {}
        self.all_batch_comboboxes = {}
        self.hbox_layout = []
        self.hlines = []
        self.finished_loading = False
        self.batches_created = False

    def load_ui(self):
        self.started = False
        self.setStyleSheet(open("style.qss", "r").read())
        self.mainvbox = QVBoxLayout()
        self.clearLayout(self.mainvbox)
        self.printer = QPrinter()

        pixmap = QPixmap('vendor.png')

        self.lblVendorImage.setPixmap(pixmap)
        self.lblVendorImage.setFixedSize(pixmap.width(), pixmap.height())

        self.txtShipTo.setObjectName('ShipTo')

        self.btnAdd = self.findChild(QPushButton, 'btnAdd')
        self.btnAdd.setObjectName('btnAdd')
        self.btnAdd.clicked.connect(partial(self.add, True, '', []))
        self.btnAdd.setShortcut('Ctrl+O')

        self.btnCreateBatch.clicked.connect(self.createBatch)
        self.btnCreateBatch.setIcon(
            QIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogNewFolder'))))
        self.btnDeleteBatch.clicked.connect(self.deleteBatch)
        self.btnDeleteBatch.setIcon(
            QIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogDiscardButton'))))

        self.batchToView.currentIndexChanged.connect(self.reloadListUI)
        self.reload_batch_view()

        self.txtSearch = SearchButtonLineEdit('search.png')
        self.txtSearch.buttonClicked.connect(self.btnsearch)
        self.txtSearch.setFont(QFont('Arial', 14))
        # main.show()
        self.txtSearch.setObjectName('Search')
        # self.txtSearch.textChanged.connect(self.search)
        self.txtSearch.returnPressed.connect(self.search)
        self.txtSearchLayout.addWidget(self.txtSearch)

        self.lblState = self.findChild(QLabel, 'lblState')
        self.lblState.setHidden(True)

        self.progressBar = self.findChild(QProgressBar, 'progressBar')
        self.progressBar.setHidden(True)
        self.progressBar.setAlignment(Qt.AlignLeft)

        # self.PrintWidget = self.findChild(QGroupBox, 'PrintWidget')
        # self.PrintWidget.setObjectName('Print')
        self.PrintWidget.setLayout(self.mainvbox)
        self.PrintWidget.setContentsMargins(0, 6, 0, 6)

        self.btnPrint.clicked.connect(
            partial(self.print_widget, self.PrintWidget))
        self.actionPrint = self.findChild(QAction, 'actionPrint')
        self.actionPrint.triggered.connect(
            partial(self.print_widget, self.PrintWidget))
        self.actionPrint.setShortcut('Ctrl+P')

        self.actionAbout = self.findChild(QAction, 'actionAbout_2')
        self.actionAbout.triggered.connect(self.openAbout)
        self.actionAbout.setIcon(QIcon(os.path.dirname(
            os.path.realpath(__file__)) + "/icon.png"))
        # self.actionAbout.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogInfoView')))

        self.actionAbout_Qt = self.findChild(QAction, 'actionAbout_Qt')
        self.actionAbout_Qt.triggered.connect(qApp.aboutQt)
        self.actionAbout_Qt.setIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_TitleBarMenuButton')))

        self.actionAdd = self.findChild(QAction, 'action_Add')
        self.actionAdd.triggered.connect(partial(self.add, True, '', []))
        self.actionAdd.setShortcut('Ctrl+A')

        self.actionCreateBatch = self.findChild(QAction, 'actionCreate_Batch_2')
        self.actionCreateBatch.setIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_FileDialogNewFolder')))
        self.actionCreateBatch.triggered.connect(partial(self.Create_saved_batch_file, ''))

        self.actionDeleteBatch = self.findChild(
            QAction, 'actionDelete_Batch_2')
        self.actionDeleteBatch.setIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_TrashIcon')))
        self.actionDeleteBatch.triggered.connect(self.Delete_saved_batch_files)

        self.actionLoadBatch = self.findChild(QMenu, 'menu_Load_Batch')
        self.actionLoadBatch.setIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_DirLinkIcon')))
        self.reload_batch_load_view()
        # self.actionLoadBatch.triggered.connect(self.Load_Saved_batch_files)

        self.actionSaveAs = self.findChild(QAction, 'action_Save_As')
        self.actionSaveAs.setIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_DriveFDIcon')))
        self.actionSaveAs.triggered.connect(partial(self.Save_batch_as, ''))

        self.actionBackup_All_Files = self.findChild(QAction, 'actionBackup_All_Files')
        self.actionBackup_All_Files.setIcon(QIcon('zip.png'))
        self.actionBackup_All_Files.triggered.connect(self.generate_backup)
        
        self.actionAbout_3.triggered.connect(self.open_about_window)
        self.actionAbout_3.setIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_MessageBoxQuestion')))

        self.started = True

        # self.print_widget()

        self.show()
        self.center()
        self.reload_auto_complete()
        self.reloadListUI()

    def resizeEvent(self, event):
        self.resized.emit()
        return super(mainwindowUI, self).resizeEvent(event)

    def getSize(self):
        global window_geometry
        window_geometry = [self.pos().x(), self.pos().y(
        ), self.frameGeometry().width(), self.frameGeometry().height()]

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls:
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            links = [str(url.toLocalFile()) for url in event.mimeData().urls()]
            self.add(False, links, [])
        else:
            event.ignore()

    def generate_backup(self): 
        self.setCursor(Qt.BusyCursor)
        t = threading.Thread(target=self.generate_backup_Thread, args=('isdone',))
        t.start()
        t.join()
        if self.returns['isdone'] == 'True':
            self.unsetCursor()
            
    def generate_backup_Thread(self, bar):
        generate_back_up_name = datetime.now().strftime("%A %B %d %Y")
        directories = ['Images/', 'Batches/']
        file_paths = []
        for directory in directories:
            file_paths += get_all_file_paths(directory) 
        with ZipFile(f'Backups/Backup - {generate_back_up_name}.zip','w', compression=zipfile.ZIP_DEFLATED) as zip: 
            for file in file_paths: 
                zip.write(file) 
            zip.write('settings.txt')
        self.returns[bar] = 'True'
    
    def start_conversion(self, files, batchToAddTo):
        self.setCursor(Qt.BusyCursor)
        self.threads = []
        converter = ConvertThread(files, batchToAddTo)
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
            # self.clearLayout(self.gridLayoutItems)
            self.reload_auto_complete()
            self.progressBar.setHidden(True)
            self.unsetCursor()
            self.reloadListUI()

    def start_image_conversion(self):
        self.setCursor(Qt.BusyCursor)
        self.threads = []
        converter = ProcessImagesThread(self.txtShipTo.text())
        converter.sig.connect(self.on_image_ready)
        self.threads.append(converter)
        converter.start()

    def on_image_ready(self):
        self.unsetCursor()

    def createBatch(self):
        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
        text, okPressed = QInputDialog.getText(
            self, "Name", "Enter Group name:", QLineEdit.Normal, "")
        if okPressed and text != '':
            with open(Data_JSON) as file:
                Data_JSON_Contents = json.load(file)
                Data_JSON_Contents[0].update({f'{text}': []})
                with open(Data_JSON, mode='w+', encoding='utf-8') as file:
                    json.dump(Data_JSON_Contents, file,
                              ensure_ascii=True, sort_keys=True)
                self.reload_batch_view()
        # self.genresComboBox.setCurrentIndex(0)
        # self.refreshNoteSettingComboBox()
        # self.updateNotes()

    def deleteBatch(self):
        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)

        text, okPressed = QInputDialog().getItem(
            self, "Select one to delete.", "Batchs:", BATCHES, 0, False)
        if okPressed:
            for _, j in enumerate(BATCHES):
                if text == j:
                    clear_batches()
                    load_batch(file_names, image_locations, quantities, description, checkmarked,
                                materials, batch_name_list, batch_index_val, BATCH=j)
                    try:
                        for file_name in image_locations:
                            os.remove(os.path.dirname(os.path.abspath(__file__)) + file_name)
                    except FileNotFoundError: pass
                    Data_JSON_Contents[0].pop(text)
                    with open(Data_JSON, mode='w+', encoding='utf-8') as file:
                        json.dump(Data_JSON_Contents, file,
                                  ensure_ascii=True)
                    self.reload_batch_view()
        # self.refreshNoteSettingComboBox()
        # self.updateNotes()
        # if len(genre_names) != 1: self.genresComboBox.setCurrentIndex(0)

    def add(self, openFileDirectory, dragDropFiles, selectedBatch):
        # open file directory
        if openFileDirectory:
            files, _ = QFileDialog.getOpenFileNames(
                self, "Add Files", "", "DXF or Image Files (*.dxf & *.png & *.jpg & *.jpeg)")
        else:
            files = dragDropFiles
        existing_files = []
        non_existing_files = []
        approved = ['.dxf', '.DXF', '.png', '.PNG', '.jpg', '.jpeg']
        files[:] = [url for url in files if any(
            sub in url for sub in approved)]
        # for i, j in enumerate(files):
        #     if j.endswith('.dxf') or j.endswith('.DXF'):
        #         pass
        #     else:
        #         files.pop(i)
        if files:
            if selectedBatch == []:
                batch_to_add_to, okPressed = QInputDialog().getItem(self, "Select an existing batch.",
                                                                    "Which batch do you want to add to:", BATCHES + ['NON_BATCH'], 0, False)
                if not okPressed:
                    return
            else:
                batch_to_add_to = selectedBatch[0]
            clear_batches()
            load_batch(file_names, image_locations, quantities, description, checkmarked,
                       materials, batch_name_list, batch_index_val, BATCH=batch_to_add_to)
            temp_fileNames = []
            # Generate file name
            for i, j in enumerate(files):
                temp_fileNames.append(j.split("/")[-1].split(".")[0])
            # idk what this does but it works and it makes it faster they say
            set_1 = set(temp_fileNames)
            # add all files to this list if it does not exist in the data.json file
            non_existing_files = [
                item for item in set_1 if item not in file_names]
            # add all files to this list if they already have been added before
            existing_files = [item for item in set_1 if item in file_names]
            non_existing_files_index = []
            new_files = []
            # loop over all files that already exist
            # if self.batchToView.currentText() == 'Everything but Part Batches': self.batches_to_load.append(NON_BATCHES[0])
            # elif self.batchToView.currentText() == 'Everything':
            #     for i in range(len(BATCHES)): self.batches_to_load.append(BATCHES[i])
            #     self.batches_to_load.append(NON_BATCHES[0])
            # elif self.batchToView.currentText() == 'All Part Batches':
            #     for i in range(len(BATCHES)): self.batches_to_load.append(BATCHES[i])
            # else:  self.batches_to_load.append(BATCHES[int(self.batchToView.currentIndex())])
            for i, j in enumerate(existing_files):
                buttonReply = QMessageBox.critical(self, f'{files[i]}', f"A file named '{j}' already exists in {batch_to_add_to}.\n\nDo you want to replace it?",
                                                   QMessageBox.YesToAll | QMessageBox.Yes | QMessageBox.Abort, QMessageBox.YesToAll)
                if buttonReply == QMessageBox.Abort:
                    return
                elif buttonReply == QMessageBox.Yes:
                    # Removes files that have already been added
                    for i, j in enumerate(temp_fileNames):
                        for o, k in enumerate(non_existing_files):
                            if j == k:
                                non_existing_files_index.append(i)
                                new_files = [files[item]
                                             for item in non_existing_files_index]
                                break
                elif buttonReply == QMessageBox.YesToAll:
                    # Removes files that have already been added
                    for i, j in enumerate(temp_fileNames):
                        for o, k in enumerate(non_existing_files):
                            if j == k:
                                non_existing_files_index.append(i)
                    new_files = [files[item]
                                 for item in non_existing_files_index]
                    break
            new_files = list(dict.fromkeys(new_files))
            if not existing_files:
                self.start_conversion(files, batch_to_add_to)
                return
            if new_files:
                self.start_conversion(new_files, batch_to_add_to)
            else:
                QMessageBox.information(self, 'All files already exist.',
                                        f"All the selected files are already added.\nThere are no new files to add.", QMessageBox.Ok, QMessageBox.Ok)

    def btnOpenPath(self, path):
        FILEBROWSER_PATH = os.path.join(os.getenv('WINDIR'), 'explorer.exe')
        path = os.path.normpath(path)
        if os.path.isdir(path):
            subprocess.run([FILEBROWSER_PATH, path], stdout=subprocess.PIPE,
                           stderr=sbuprocess.PIPE, stdin=subprocess.PIPE)
        elif os.path.isfile(path):
            subprocess.run([FILEBROWSER_PATH, '/select,', os.path.normpath(path)],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)

    def openImage(self, path):
        self.getSize()
        self.vi = QImageViewer(path)
        self.vi.show()
        # self.close()

    def open_about_window(self):
        time_now = datetime.now()
        diffrence = (time_now - latest_update_date).days
        QMessageBox.information(
            self, f'{title}', f"Version: {version}\nLast Update: {diffrence} days ago on {latest_update_date_formated}.\nDeveloped by: TheCodingJ's", QMessageBox.Ok, QMessageBox.Ok)

    def openAbout(self):
        self.about = aboutwindowUI()
        self.about.show()

    def delete(self, batch, index, layout, line):
        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
        clear_batches()
        load_batch(file_names, image_locations, quantities, description, checkmarked,
                   materials, batch_name_list, batch_index_val, BATCH=batch)
        Data_JSON_Contents[0][batch].pop(index)
        # self.delete_buttons.pop(index)
        # self.all_batch_checkboxes[batch].pop(index)
        # self.all_batch_delete_buttons[batch].pop(index)
        # self.hbox_layout.pop(index)
        # self.hlines.pop(index)
        with open(Data_JSON, mode='w+', encoding='utf-8') as file:
            json.dump(Data_JSON_Contents, file,
                      ensure_ascii=True)
        # sort_data(batch)
        # self.clearLayout(layout)
        # line.deleteLater()
        try: os.remove(os.path.dirname(os.path.abspath(__file__)) + image_locations[index])
        except FileNotFoundError: pass
        # clear_batches()
        # for index_of_batch, batch_name in enumerate(self.batches_to_load):
        #     load_batch(file_names, image_locations, quantities, description, checkmarked,
        #                materials, batch_name_list, batch_index_val, BATCH=batch_name)
        # for i, j in enumerate(self.all_batch_delete_buttons[batch]):
        #     j.clicked.disconnect()
        #     j.clicked.connect(
        #         partial(self.delete, batch_name_list[i], i, self.hbox_layout[i], self.hlines[i]))
        # if not file_names: self.reloadListUI()
        self.reloadListUI()

    def clearLayout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()
                else:
                    self.clearLayout(item.layout())

    def print_widget(self, Print_Widget_everything, printer):
        # self.drawText(event, qp)
        batch_names = [batch.title() for batch in batch_group_box_GUI]
        # for index, batch_name in enumerate(self.all_batch_checkboxes):
        #     if self.all_batch_checkboxes[batch_names[index]] == []:
        #         # del self.all_batch_checkboxes[index]
        #         batch_names.pop(index)
        #         batch_group_box_GUI.pop(index)
        # batch_names += ['Everything']
        # if 'NON_BATCH' in batch_names: del batch_names[-1]

        if len(batch_names) > 1:
            batch_to_add_print, okPressed = QInputDialog().getItem(self, "Select a batch.",
                                                                   "Select a batch to print:",
                                                                   batch_names + ['Everything'], 0, False)
            if okPressed:
                if batch_to_add_print == 'Everything':
                    screen = self.PrintWidget.grab()
                    image = QImage(screen)
                    image.save("view.png")
                    for num, _ in enumerate(batch_group_box_GUI):
                        screen = batch_group_box_GUI[num].grab()
                        image = QImage(screen)
                        image.save(f"Capture/capture - {num}.png")
                else:
                    for i, j in enumerate(batch_names):
                        if batch_to_add_print == j:
                            screen = batch_group_box_GUI[i].grab()
                            image = QImage(screen)
                            image.save("Capture/capture - 0.png")
                            image.save("view.png")
            else:
                return
        else:
            screen = self.PrintWidget.grab()
            image = QImage(screen)
            image.save("view.png")
            for num, _ in enumerate(batch_group_box_GUI):
                screen = batch_group_box_GUI[num].grab()
                image = QImage(screen)
                image.save(f"Capture/capture - {num}.png")
        self.openImage('view.png')
        self.start_image_conversion()

    def reload_batch_view(self):
        global BATCHES
        load_batches(BATCHES)
        del BATCHES[-1]
        self.batchToView.clear()
        if not BATCHES:
            self.batches_created = False
            self.batchToView.addItems(
                BATCHES + ['Everything but Part Batches'])
            self.batchToView.insertSeparator(len(BATCHES) + 1)
            # self.batchToView.setItemIcon(len(BATCHES)+2, QIcon(
            #     self.style().standardIcon(getattr(QStyle, 'SP_FileDialogNewFolder'))))
            self.btnCreateBatch.setHidden(False)
            self.btnDeleteBatch.setHidden(True)
        else:
            self.batches_created = True
            self.batchToView.addItems(
                BATCHES + ['Everything but Part Batches', 'All Part Batches', 'Everything'])
            self.batchToView.insertSeparator(len(BATCHES))
            self.btnCreateBatch.setHidden(False)
            self.btnDeleteBatch.setHidden(False)
        self.reloadListUI()
        # self.batchToView.insertSeparator(len(BATCHES) + 4)
        # self.batchToView.setItemIcon(len(BATCHES) + 5, QIcon(
        #     self.style().standardIcon(getattr(QStyle, 'SP_FileDialogNewFolder'))))
        # self.batchToView.setItemIcon(len(
        #     BATCHES) + 6, QIcon(self.style().standardIcon(getattr(QStyle, 'SP_DialogDiscardButton'))))

    def Save_batch_as(self, string = ''):
        global SAVED_DATA_JSON_FILES
        fileName, _ = QFileDialog.getSaveFileName(self,"Save Batch File", os.path.dirname(os.path.abspath(__file__)) + '/Batches',"JSON Files (*.json)")
        if fileName:
            if not os.path.isfile(fileName):
                if not fileName.endswith('.json'):
                    fileName += '.json'
                try:
                    shutil.copy(os.path.dirname(os.path.abspath(__file__)) + '/' + Data_JSON, fileName, follow_symlinks=True)
                except PermissionError:
                    with open(os.path.dirname(os.path.abspath(__file__)) + '/' + Data_JSON, 'rb') as src, open(fileName, 'wb') as dst: dst.write(src.read())
                except:
                    QMessageBox.critical(self, 'Permission denied', "Permission denied.\n\nTry running the program in Administrator mode.", QMessageBox.Ok, QMessageBox.Ok)
                    return
            # else:
            #     text = fileName.split("/")[-1].split(".")[0]
            #     buttonReply = QMessageBox.question(self, 'File already Exists', f"{text} already exists.\n\nWould you like to try again?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No)
            #     if buttonReply == QMessageBox.Yes: self.Save_batch_as(text)
            #     return
        SAVED_DATA_JSON_FILES = os.listdir('Batches/')
        self.reload_batch_load_view()

    def Create_saved_batch_file(self, string=""):
        global SAVED_DATA_JSON_FILES
        text, okPressed = QInputDialog.getText(
            self, "Name", "Enter New Batch name:", QLineEdit.Normal, string)
        if okPressed and text != '':
            if not text.endswith('.json'): text += '.json'
            if not os.path.isfile("Batches/" + text):
                with open('Batches/' + text, 'w+') as file: file.write('[{"NON_BATCH":[]}]')
            else:
                text.replace('.json', '')
                buttonReply = QMessageBox.question(self, 'File already Exists', f"{text} already exists.\n\nWould you like to try again?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.No)
                if buttonReply == QMessageBox.Yes: self.Create_saved_batch_file(text)
                return
            SAVED_DATA_JSON_FILES = os.listdir('Batches/')
            self.reload_batch_load_view()
            
    def Delete_saved_batch_files(self):
        global BATCHES, Data_JSON, SAVED_DATA_JSON_FILES
        current_open_batch = Data_JSON
        view = SAVED_DATA_JSON_FILES
        [v.replace('.json', '') for v in view]
        text, okPressed = QInputDialog().getItem(
            self, "Select one to delete.", "Saved Batches:", view, 0, False)
        if okPressed:
            for _, j in enumerate(SAVED_DATA_JSON_FILES):
                if text == j:
                    Data_JSON = 'Batches/' + text
                    BATCHES.clear()
                    load_batches(BATCHES)
                    # SAVED_DATA_JSON_FILES.pop(_)
                    clear_batches()
                    for batch_name in BATCHES:
                        load_batch(file_names, image_locations, quantities, description, checkmarked,
                                    materials, batch_name_list, batch_index_val, BATCH=batch_name)
                    try:
                        for file_name in image_locations:
                            os.remove(os.path.dirname(os.path.abspath(__file__)) + file_name)
                    except FileNotFoundError: 
                        pass
            os.remove('Batches/' + text)
            SAVED_DATA_JSON_FILES = os.listdir('Batches/')
            text = 'Batches/' + text
            try:
                if current_open_batch == text: Data_JSON = 'Batches/' + SAVED_DATA_JSON_FILES[0]
                else: Data_JSON = current_open_batch
            except IndexError:
                with open('Batches/Batch #1.json', 'w+') as f:
                    f.write('[{"NON_BATCH":[]}]')
                    Data_JSON = 'Batches/Batch.json'
            save = Data_JSON.replace('Batches/', '')
            with open(SETTINGS_FILE, 'w+') as file: file.write(save)
            SAVED_DATA_JSON_FILES = os.listdir('Batches/')
            BATCHES.clear()
            load_batches(BATCHES)
            self.reload_batch_load_view()
            self.reload_batch_view()
            self.title_json = Data_JSON.replace('Batches/','').replace('.json','')
            self.txtCurrentViewingBatch.setText(self.title_json)
            self.setWindowTitle(f'{title} - {version} - {self.title_json}')
    
    def reload_batch_load_view(self):
        self.actionLoadBatch.clear()
        for saved_batch_name in SAVED_DATA_JSON_FILES:
            saved_batch_name = saved_batch_name.replace('.json', '')
            action_load = QAction(saved_batch_name, self)
            action_load.setIcon(self.style().standardIcon(
                getattr(QStyle, 'SP_FileLinkIcon')))
            action_load.triggered.connect(partial(self.Load_saved_batch, saved_batch_name))
            self.actionLoadBatch.addAction(action_load)

    def Load_saved_batch(self, batch_name):
        global Data_JSON
        Data_JSON = 'Batches/' + batch_name + '.json'
        BATCHES.clear()
        self.reload_batch_view()
        self.reload_auto_complete()
        save = Data_JSON.replace('Batches/', '')
        with open(SETTINGS_FILE, 'w+') as file: file.write(save)
        self.title_json = Data_JSON.replace('Batches/','').replace('.json','')
        self.setWindowTitle(f'{title} - {version} - {self.title_json}')
        self.txtCurrentViewingBatch.setText(self.title_json)

    def reload_auto_complete(self):
        clear_batches()
        for _, batch_name in enumerate(BATCHES):
            load_batch(file_names, image_locations, quantities, description, checkmarked,
                       materials, batch_name_list, batch_index_val, BATCH=batch_name)
        model = QStringListModel()
        model.setStringList(file_names)
        completer = QCompleter()
        completer.setModel(model)
        self.txtSearch.setCompleter(completer)

    def reloadListUI(self):
        if not self.started:
            return
        self.setCursor(Qt.BusyCursor)
        self.clearLayout(self.mainvbox)
        self.clearLayout(self.GridLayoutHeaders)
        self.batches_to_load.clear()
        self.hbox_layout.clear()
        self.button_images.clear()
        self.images_path.clear()
        self.hlines.clear()

        clear_batches()
        try:
            if self.batchToView.currentText() == 'Everything but Part Batches':
                self.batches_to_load.append(NON_BATCHES[0])
            elif self.batchToView.currentText() == 'Everything':
                for BATCH_ in BATCHES:
                    self.batches_to_load.append(BATCH_)
                self.batches_to_load.append(NON_BATCHES[0])
            elif self.batchToView.currentText() == 'All Part Batches':
                for BATCH in BATCHES:
                    self.batches_to_load.append(BATCH)
            else:
                self.batches_to_load.append(
                    BATCHES[int(self.batchToView.currentIndex())])

        except:
            pass
        if len(self.batches_to_load) == 0:
            self.batches_to_load.append(NON_BATCHES[0])

        self.btnPrint.setHidden(self.batchToView.currentText() in [
                                'Everything', 'All Part Batches'])

        # self.btnPrint.setHidden(True)
        for index, name in enumerate(['             Name:', 'Description:', 'Material:', 'Quantity:', 'Image:', 'Checkmark:']):
            self.lbl = QLabel(name)
            self.GridLayoutHeaders.addWidget(self.lbl, 0, index)

        batch_group_box_GUI.clear()
        batch_vbox_GUI = []
        batch_lengths = []
        orginized_length_of_batches = {}
        orginized_file_names = {}
        self.all_batch_checkboxes.clear()
        self.all_batch_delete_buttons.clear()
        self.all_batch_comboboxes.clear()
        for name in self.batches_to_load:
            orginized_length_of_batches.update({name: []})
            orginized_file_names.update({name: []})
            self.all_batch_checkboxes.update({name: []})
            self.all_batch_delete_buttons.update({name: []})
            self.all_batch_comboboxes.update({name: []})
            # self.button_images.update({name: []})

        self.item_added_count = 0

        first_batch = ''
        for _, batch_name in enumerate(self.batches_to_load):
            if first_batch == '':
                first_batch = batch_name
            clear_batches()
            load_batch(file_names, image_locations, quantities, description, checkmarked,
                       materials, batch_name_list, batch_index_val, BATCH=batch_name)
            if self.txtSearch.text() == '':
                orginized_length_of_batches[batch_name].append(len(file_names))
            else:
                orginized_length_of_batches[batch_name].append(0)
            if len(file_names) == 0:
                batch_lengths.append('EMPTY')
            for i in range(len(file_names)):
                orginized_file_names[batch_name].append(file_names[i])
                batch_lengths.append(i)

        self.current_batch_index = 0
        clear_batches()
        for _, batch_name in enumerate(self.batches_to_load):
            load_batch(file_names, image_locations, quantities, description, checkmarked,
                       materials, batch_name_list, batch_index_val, BATCH=batch_name)
            groupbox = QGroupBox(batch_name)
            vbox = QVBoxLayout()
            groupbox.setContentsMargins(0, 6, 0, 6)
            groupbox.setObjectName('Batch')
            groupbox.setFont(QFont('Arial', 15))
            vbox.addStretch(1)
            vbox.setSpacing(6)
            batch_vbox_GUI.append(vbox)
            batch_group_box_GUI.append(groupbox)
        self.temp_index = 0
        if len(file_names) > 0:
            list_to_check_adding = [file_names[i] for i, _ in enumerate(file_names) if (self.txtSearch.text(
            ) != '' and self.txtSearch.text().lower() in file_names[i].lower() or self.txtSearch.text() == '')]
            items_to_add = list_to_check_adding != []
        for _, name_batch in enumerate(self.batches_to_load):
            for i, _ in enumerate(orginized_file_names[name_batch]):
                if (self.txtSearch.text() != '' and self.txtSearch.text().lower() in orginized_file_names[name_batch][i].lower()):
                    orginized_length_of_batches[name_batch][0] += 1
        length_of_batches = [
            orginized_length_of_batches[name_batch][0]
            for _, name_batch in enumerate(self.batches_to_load)
        ]

        if len(self.batches_to_load) > 1 and any(x != batch_lengths[0] for x in batch_lengths):
            temp_amount_of_zeros_found = 0
            for index, number in enumerate(batch_lengths):
                if number == 'EMPTY':
                    temp_amount_of_zeros_found += 1
                    for i, name in enumerate(self.batches_to_load):
                        if name == self.batches_to_load[temp_amount_of_zeros_found-1]:
                            self.batches_to_load.pop(
                                temp_amount_of_zeros_found-1)
                            batch_vbox_GUI.pop(temp_amount_of_zeros_found-1)
                            length_of_batches.pop(temp_amount_of_zeros_found-1)
                            batch_group_box_GUI.pop(
                                temp_amount_of_zeros_found-1)
                            batch_lengths.pop(index)
                elif number == 0:
                    temp_amount_of_zeros_found += 1
        self.txtBoxList.clear()
        self.HAS_SHOWN_NO_BATCH_OR_NOT_FOUND = False

        if len(file_names) > 0:
            self._iter = iter(range(len(file_names)))
            self._timer = QTimer(interval=10, timeout=partial(self.load_UI_objects, length_of_batches,
                                                              batch_lengths, batch_group_box_GUI, batch_vbox_GUI, self.batches_to_load, True, items_to_add))
            self._timer.start()
        else:
            self.load_UI_objects(length_of_batches, batch_lengths, batch_group_box_GUI,
                                 batch_vbox_GUI, self.batches_to_load, False, True)

    def load_UI_objects(self, length_of_batches, batch_lengths, groupboxes, vboxes, batch_names, INTERVAL_LOAD, ITEMS_TO_ADD):
        try:
            i = next(self._iter) if INTERVAL_LOAD else 0
        except StopIteration:
            # self.actionPrint.setEnabled(True)
            self.actionPrint.setEnabled(self.batchToView.currentText() not in [
                'Everything', 'All Part Batches'])
            self.btnPrint.setEnabled(True)
            self._timer.stop()
            self.unsetCursor()
            self.progressBar.setValue(len(file_names))
            self.progressBar.setFormat(f' Finished! 100%')
            loop = QEventLoop()
            QTimer.singleShot(500, loop.quit)
            loop.exec_()
            self.progressBar.setHidden(True)
            self.finished_loading = True
            self.btnCreateBatch.setEnabled(True)
            self.btnDeleteBatch.setEnabled(True)
            self.batchToView.setEnabled(True)

        else:
            self.btnCreateBatch.setEnabled(False)
            self.batchToView.setEnabled(False)
            self.btnDeleteBatch.setEnabled(False)
            self.progressBar.setHidden(False)
            self.btnPrint.setEnabled(False)
            self.actionPrint.setEnabled(False)
            self.progressBar.setValue(i)
            self.progressBar.setMaximum(len(file_names))
            if len(batch_names) > 1 and batch_lengths[i] == 0 and i != 0:
                self.current_batch_index += 1
                self.txtBoxList.clear()
                self.temp_index = 0
            vbox = vboxes[self.current_batch_index]
            groupbox = groupboxes[self.current_batch_index]
            batch_name = batch_names[self.current_batch_index]
            if INTERVAL_LOAD:
                if sum(length_of_batches) != 0:
                    self.progressBar.setFormat(
                        f' Loading... {int(self.item_added_count/sum(length_of_batches)*100)}%')
                else:
                    self.progressBar.setFormat(
                        f' Loading... {int(self.item_added_count/(sum(length_of_batches)+1)*100)}%')
                l = length_of_batches[self.current_batch_index]
                if (self.txtSearch.text() != '' and self.txtSearch.text().lower() in file_names[i].lower() or self.txtSearch.text() == ''):
                    self.item_added_count += 1

                    hbox = QHBoxLayout()
                    line = QHLine()

                    self.label = QPushButton(file_names[i])
                    self.label.setCursor(Qt.PointingHandCursor)
                    self.label.setContextMenuPolicy(Qt.CustomContextMenu)
                    self.label.customContextMenuRequested.connect(partial(
                        self.menu_move_to, batch_name_list[i], file_names[i], batch_index_val[i], self.temp_index, hbox, line, self.label))
                    self.label.clicked.connect(partial(self.btnOpenPath, os.path.dirname(
                        os.path.abspath(__file__)) + image_locations[i]))
                    self.label.setObjectName('Name')
                    self.label.setToolTip(
                        f'Opens {file_names[i]} in file explorer.')
                    self.label.setFont(QFont('Arial', 14))
                    self.label.setFlat(True)
                    self.label.setFixedSize(300, 60)

                    self.textBoxDescription = TextEdit(self)
                    self.textBoxDescription.setAlignment(QtCore.Qt.AlignCenter)
                    self.textBoxDescription.setText(str(description[i]))
                    self.textBoxDescription.editingFinished.connect(
                        partial(self.saveLineEdit, self.textBoxDescription, batch_index_val[i], 'Str', batch_name_list[i]))
                    self.textBoxDescription.setFocusPolicy(Qt.StrongFocus)
                    self.textBoxDescription.setPlaceholderText(
                        'Enter notes here...')
                    self.textBoxDescription.setFixedSize(100, 60)

                    # creating a line edit
                    self.edit = QLineEdit(self)
                    self.edit.editingFinished.connect(
                        partial(self.saveLineEdit, self.edit, batch_index_val[i], 'ComboEdit', batch_name_list[i]))
                    self.edit.setFont(QFont('Arial', 14))
                    # setting line edit
                    self.comboBoxMaterial = QComboBox()
                    self.comboBoxMaterial.setLineEdit(self.edit)
                    self.comboBoxMaterial.activated.connect(partial(
                        self.saveLineEdit, self.comboBoxMaterial, batch_index_val[i], 'Combo', batch_name_list[i]))
                    self.comboBoxMaterial.addItems(self.materials)
                    for index, j in enumerate(materials[i]):
                        if j == self.materials[index]:
                            self.comboBoxMaterial.setCurrentIndex(
                                int(materials[index]))
                        else:
                            self.edit.setText(materials[i])
                    self.comboBoxMaterial.setFixedSize(250, 60)
                    self.comboBoxMaterial.setContextMenuPolicy(Qt.CustomContextMenu)
                    self.comboBoxMaterial.customContextMenuRequested.connect(partial(
                        self.menu_change_all, batch_name_list[i], self.comboBoxMaterial.currentText(), self.comboBoxMaterial))
                    self.all_batch_comboboxes[batch_name].append(self.edit)

                    self.textBoxInput = QLineEdit("1")
                    self.textBoxInput.setObjectName('Quantity')
                    self.textBoxInput.setAlignment(QtCore.Qt.AlignCenter)
                    self.textBoxInput.setValidator(QIntValidator())
                    self.textBoxInput.setText(str(quantities[i]))
                    self.textBoxInput.editingFinished.connect(
                        partial(self.saveLineEdit, self.textBoxInput, batch_index_val[i], 'Int', batch_name_list[i]))
                    self.textBoxInput.setFocusPolicy(Qt.StrongFocus)
                    self.textBoxInput.setFixedSize(60, 60)
                    self.txtBoxList.append(self.textBoxInput)

                    self.btnImage = QPushButton()
                    self.btnImage.setCursor(Qt.PointingHandCursor)
                    self.btnImage.setObjectName('btnImage')
                    self.btnImage.clicked.connect(partial(self.openImage, os.path.dirname(
                        os.path.abspath(__file__)) + image_locations[i]))
                    self.images_path.append(os.path.dirname(
                        os.path.abspath(__file__)) + image_locations[i])
                    self.btnImage.setIcon(QIcon(os.path.dirname(
                        os.path.abspath(__file__)) + image_locations[i]))
                    self.btnImage.setIconSize(QSize(150-6, 60-6))

                    self.btnImage.setFixedSize(250, 60)
                    self.btnImage.setFlat(True)
                    self.btnImage.setToolTip(os.path.dirname(
                        os.path.abspath(__file__)) + image_locations[i])
                    self.btnImage.setContextMenuPolicy(Qt.CustomContextMenu)
                    self.btnImage.customContextMenuRequested.connect(partial(self.menu_print, os.path.dirname(
                        os.path.abspath(__file__)) + image_locations[i], self.btnImage))
                    self.button_images.append(self.btnImage)

                    self.checkmark = QCheckBox()
                    self.checkmark.setObjectName('checkbox')
                    self.checkmark.setCursor(Qt.PointingHandCursor)
                    self.checkmark.setChecked(checkmarked[i] == 'True')
                    self.checkmark.setFixedSize(60, 60)
                    self.checkmark.stateChanged.connect(
                        partial(self.saveLineEdit, self.checkmark, batch_index_val[i], 'Chk', batch_name_list[i]))
                    self.checkmark.setContextMenuPolicy(Qt.CustomContextMenu)
                    self.checkmark.customContextMenuRequested.connect(
                        partial(self.menu_check_or_uncheck_all, batch_name_list[i], self.checkmark))
                    self.all_batch_checkboxes[batch_name].append(
                        self.checkmark)

                    self.btnDelete = QPushButton()
                    self.btnDelete.setFlat(True)
                    self.btnDelete.setToolTip('Will delete: ' + os.path.dirname(
                        os.path.abspath(__file__)) + image_locations[i] + ' and all of the saved data.')
                    self.btnDelete.setFixedSize(32, 32)
                    self.btnDelete.setIcon(self.style().standardIcon(
                        getattr(QStyle, 'SP_DialogDiscardButton')))
                    self.hbox_layout.append(hbox)
                    self.btnDelete.clicked.connect(
                        partial(self.delete, batch_name_list[i], self.temp_index, hbox, line))
                    # for k in range(5):
                    # self.delete_buttons.append(self.btnDelete)
                    self.all_batch_delete_buttons[batch_name].append(
                        self.btnDelete)
                    hbox.addWidget(self.label)
                    hbox.addWidget(self.textBoxDescription)
                    hbox.addWidget(self.comboBoxMaterial)
                    hbox.addWidget(self.textBoxInput)
                    hbox.addWidget(self.btnImage)
                    hbox.addWidget(self.checkmark)
                    hbox.addWidget(self.btnDelete)
                    vbox.addLayout(hbox)
                    if self.temp_index + 1 != l:
                        vbox.addWidget(line)
                    self.hlines.append(line)
                    self.temp_index += 1
            groupbox.setLayout(vbox)
            if self.txtBoxList:
                self.mainvbox.addWidget(groupbox)
            if not self.batches_created and len(file_names) < 1 and not self.HAS_SHOWN_NO_BATCH_OR_NOT_FOUND:
                # self.clearLayout(self.mainvbox)
                label = QLabel()
                label.setText(
                    f'<br>You have no Batches.\n<br><a href=\"https://\">Create a Batch</a>')
                clickableLabel(label).connect(self.createBatch)
                label.setObjectName('Name')
                label.setAlignment(Qt.AlignCenter)
                hbox = QHBoxLayout()
                hbox.addWidget(label)
                vbox.addLayout(hbox)
                groupbox.setLayout(vbox)
                self.mainvbox.addWidget(groupbox)
                self.btnPrint.setEnabled(False)
                self.progressBar.setHidden(True)
                self.finished_loading = True
                self.btnCreateBatch.setEnabled(True)
                self.btnDeleteBatch.setEnabled(True)
                self.batchToView.setEnabled(True)
                self.unsetCursor()
                self.HAS_SHOWN_NO_BATCH_OR_NOT_FOUND = True
                return
            if not self.txtBoxList and self.item_added_count == 0 and not self.HAS_SHOWN_NO_BATCH_OR_NOT_FOUND:
                # self.clearLayout(self.mainvbox)
                label = QLabel()
                if not file_names:
                    label.setText(
                        f'<br>Drag files here to add them to a Batch\n<br><a href=\"https://\">Or Choose your files</a>')
                    if self.batchToView.currentText() in [
                        'All Part Batches',
                        'Everything',
                    ]:
                        clickableLabel(label).connect(
                            partial(self.add, True, '', []))
                    else:
                        clickableLabel(label).connect(
                            partial(self.add, True, '', batch_names))
                if not ITEMS_TO_ADD:
                    label.setText(
                        f'Could not find a part named: "{self.txtSearch.text()}"')
                label.setObjectName('Name')
                label.setAlignment(Qt.AlignCenter)
                if len(batch_lengths) <= 1:
                    hbox = QHBoxLayout()
                    if not ITEMS_TO_ADD:
                        label.setText(
                            f'Could not find a part named: "{self.txtSearch.text()}"')
                    hbox.addWidget(label)
                    vbox.addLayout(hbox)
                    groupbox.setLayout(vbox)
                    self.mainvbox.addWidget(groupbox)
                else:
                    self.mainvbox.addWidget(label)
                self.HAS_SHOWN_NO_BATCH_OR_NOT_FOUND = True
            if not INTERVAL_LOAD:
                self.progressBar.setHidden(True)
                self.unsetCursor()
                self.btnCreateBatch.setEnabled(True)
                self.btnDeleteBatch.setEnabled(True)
                self.batchToView.setEnabled(True)
                self.finished_loading = True

    def menu_print(self, path, button, point):
        popMenu = QMenu(self)
        print_ = QAction('Print', self)
        print_.triggered.connect(partial(self.openImage, path))
        popMenu.addAction(print_)
        popMenu.exec_(button.mapToGlobal(point))
    # CHECK BOX MENU
    def menu_check_or_uncheck_all(self, BATCH_NAME, checkbox, point):
        popMenu = QMenu(self)
        check_all_action = QAction('Check All', self)
        check_all_action.triggered.connect(
            partial(self.check_all, BATCH_NAME, True))
        popMenu.addAction(check_all_action)
        uncheck_all_action = QAction('Un-Check All', self)
        uncheck_all_action.triggered.connect(
            partial(self.check_all, BATCH_NAME, False))
        popMenu.addAction(uncheck_all_action)

        popMenu.exec_(checkbox.mapToGlobal(point))
    @QtCore.pyqtSlot(QAction)
    def check_all(self, BATCH, TrueOrFalse):
        self.setCursor(Qt.BusyCursor)

        self._iter2 = iter(range(len(self.all_batch_checkboxes[BATCH])))
        self._timer2 = QTimer(interval=10, timeout=partial(
            self.checkIter, BATCH, TrueOrFalse, self.all_batch_checkboxes))
        self._timer2.start()
        t = threading.Thread(target=self.check_all_Thread,
                             args=('isdone', BATCH, TrueOrFalse,))
        t.start()
        t.join()
        if self.returns['isdone'] == 'True':
            self.unsetCursor()

    def checkIter(self, BATCH, TrueOrFalse, all_batch_checkboxes):
        try:
            i = next(self._iter2)
        except StopIteration:
            self._timer2.stop()
        else:
            all_batch_checkboxes[BATCH][i].setChecked(TrueOrFalse)

    def check_all_Thread(self, bar, BATCH, TrueOrFalse):
        clear_batches()
        load_batch(file_names, image_locations, quantities, description,
                   checkmarked, materials, batch_name_list, batch_index_val, BATCH=BATCH)
        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
        for index, batch_name in enumerate(Data_JSON_Contents):
            Data_JSON_Contents[0][BATCH].pop(0)
            Data_JSON_Contents[0][BATCH].append({
                'fileName': [file_names[index]],
                'imgLoc': [image_locations[index]],
                'quantity': [quantities[index]],
                'description': [description[index]],
                'checked': [f"{TrueOrFalse}"],
                'material': [materials[index]]
            })
        with open(Data_JSON, mode='w+', encoding='utf-8') as file:
            json.dump(Data_JSON_Contents, file,
                      ensure_ascii=True)
        sort_data(BATCH)
        self.returns[bar] = 'True'

    # ----------------------------------------------
    # COMBO BOX MENU

    def menu_change_all(self, BATCH_NAME, CURRENT_TEXT, button, point):
        print(CURRENT_TEXT)
        popMenu = QMenu(self)
        all_BATCHES = BATCHES + ['NON_BATCH']

        change_all_to = popMenu.addMenu('Change all to')
        change_all_custom = QAction('Change all to custom material')
        change_all_custom.triggered.connect(partial(
            self.change_all_materials, BATCH_NAME, '', True))
        if len(all_BATCHES) > 1:
            for mat_name in self.materials:
                mat_action = QAction(mat_name, self)
                mat_action.triggered.connect(partial(
                    self.change_all_materials, BATCH_NAME, mat_name))
                change_all_to.addAction(mat_action)
            popMenu.addAction(change_all_custom)
            popMenu.addMenu(change_all_to)
        popMenu.exec_(button.mapToGlobal(point))

    def changeMatIter(self, BATCH, material_name):
        try: i = next(self._iter3)
        except StopIteration: self._timer3.stop()
        else: self.all_batch_comboboxes[BATCH][i].setText(material_name)
    @QtCore.pyqtSlot(QAction)
    def change_all_materials(self, BATCH_NAME, material_name, custom = False):
        if custom:
            text, okPressed = QInputDialog.getText(
                self, "Material Name", "Enter Custom Material name:", QLineEdit.Normal, "")
            if okPressed and text != '': material_name = text
            else: return
        self._iter3 = iter(range(len(self.all_batch_comboboxes[BATCH_NAME])))
        self._timer3 = QTimer(interval=10, timeout=partial(
            self.changeMatIter, BATCH_NAME, material_name))
        self._timer3.start()
        t = threading.Thread(target=self.change_all_materials_Thread, args=('isdone', BATCH_NAME, material_name))
        t.start()
        t.join()
        if self.returns['isdone'] == 'True': self.unsetCursor()

    def change_all_materials_Thread(self, bar, BATCH_NAME, material_name):
        clear_batches()
        load_batch(file_names, image_locations, quantities, description, checkmarked,
                   materials, batch_name_list, batch_index_val, BATCH=BATCH_NAME)
        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
        for index, _ in enumerate(file_names):
            Data_JSON_Contents[0][BATCH_NAME].pop(0)
            Data_JSON_Contents[0][BATCH_NAME].append({
                'fileName': [file_names[index]],
                'imgLoc': [image_locations[index]],
                'quantity': [int(quantities[index])],
                'description': [description[index]],
                'checked': [checkmarked[index]],
                'material': [material_name]
            })
        with open(Data_JSON, mode='w+', encoding='utf-8') as file:
            json.dump(Data_JSON_Contents, file, ensure_ascii=True)
        self.returns[bar] = 'True'

    # TEXT BUTTOM MENU
    def menu_move_to(self, BATCH_FROM, name, index, delete_index, layout, line, button, point):
        popMenu = QMenu(self)
        all_BATCHES = BATCHES + ['NON_BATCH']
        rename = QAction('Rename')
        rename.triggered.connect(
            partial(self.rename_part, BATCH_FROM, name, index))
        if len(all_BATCHES) > 1:
            move = popMenu.addMenu('Move to')
            move_all = popMenu.addMenu('Move all to')
            for batch_name in all_BATCHES:
                if batch_name != BATCH_FROM:
                    batch_action = QAction(batch_name, self)
                    batch_action.triggered.connect(partial(
                        self.move_part, BATCH_FROM, batch_action, name, index, delete_index, layout, line,))
                    move.addAction(batch_action)

                    batch_action_move_all = QAction(batch_name, self)
                    batch_action_move_all.triggered.connect(partial(
                        self.move_all_parts, BATCH_FROM, batch_action_move_all))
                    move_all.addAction(batch_action_move_all)
            popMenu.addMenu(move)
            popMenu.addMenu(move_all)
        popMenu.addAction(rename)
        popMenu.exec_(button.mapToGlobal(point))
    @QtCore.pyqtSlot(QAction)
    def move_part(self, BATCH_FROM, BATCH_TO, part_name, index, delete_index, layout, line):
        self.setCursor(Qt.BusyCursor)
        # self.delete(BATCH_FROM, delete_index, layout, line)
        t = threading.Thread(target=self.move_part_Thread, args=(
            'isdone', BATCH_FROM, BATCH_TO.text(), part_name, index))
        t.start()
        t.join()
        if self.returns['isdone'] == 'True':
            self.reloadListUI()
            self.unsetCursor()
        elif self.returns['isdone'] == 'File Exists':
            QMessageBox.information(self, 'All files already exist.',
                                    f'That file already exists in "{BATCH_TO.text()}".', QMessageBox.Ok, QMessageBox.Ok)
            self.unsetCursor()
    @QtCore.pyqtSlot(QAction)
    def move_all_parts(self, BATCH_FROM, BATCH_TO):
        self.setCursor(Qt.BusyCursor)
        # self.delete(BATCH_FROM, delete_index, layout, line)
        t = threading.Thread(target=self.move_all_parts_Thread, args=(
            'isdone', BATCH_FROM, BATCH_TO.text()))
        t.start()
        t.join()
        if self.returns['isdone'] == 'True':
            self.reloadListUI()
            self.unsetCursor()
        elif self.returns['isdone'] == 'File Exists':
            QMessageBox.information(self, 'All files already exist.',
                                    f'That file already exists in "{BATCH_TO.text()}".', QMessageBox.Ok, QMessageBox.Ok)
            self.unsetCursor()
    @QtCore.pyqtSlot(QAction)
    def rename_part(self, BATCH, name, index):
        text, okPressed = QInputDialog.getText(
            self, "Rename part name", "New part name:", QLineEdit.Normal, name)
        if okPressed and text != '':
            self.setCursor(Qt.BusyCursor)
            self.rename_part_Thread(BATCH, text, index)

    def rename_part_Thread(self, BATCH, text, index):
        clear_batches()
        load_batch(file_names, image_locations, quantities, description, checkmarked,
                   materials, batch_name_list, batch_index_val, BATCH=BATCH)
        new_file_path = f'/Images/{text}.png'
        new_name = text
        for existing_file_names in file_names:
            if new_name == existing_file_names:
                button = QMessageBox.information(self, 'That file already exist.', f'That file already exists.\nWould you like to try again?',
                                                 QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel, QMessageBox.Cancel)
                if button == QMessageBox.Yes:
                    self.rename_part(BATCH, new_name, index)
                return
                # if self.returns['isdone'] == 'True': self.reloadListUI()

        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
        Data_JSON_Contents[0][BATCH].pop(index)
        Data_JSON_Contents[0][BATCH].append({
            'fileName': [new_name],
            'imgLoc': [new_file_path],
            'quantity': [quantities[index]],
            'description': [description[index]],
            'checked': [checkmarked[index]],
            'material': [materials[index]]
        })
        with open(Data_JSON, mode='w+', encoding='utf-8') as file:
            json.dump(Data_JSON_Contents, file,
                      ensure_ascii=True, sort_keys=True)
        os.rename(os.path.dirname(os.path.abspath(__file__)) +
                  image_locations[index], os.path.dirname(os.path.abspath(__file__)) + new_file_path)
        sort_data(BATCH)
        self.reloadListUI()
        self.unsetCursor()
        # self.rename_part(BATCH, name, index)
        # t = threading.Thread(target=self.rename_part_Thread, args=('isdone', BATCH, new_name, new_file_path, index,))
        # t.start()
        # t.join()

        # self.returns[bar] = 'True'

    def move_part_Thread(self, bar, BATCH_FROM, BATCH_TO, name, index):
        clear_batches()
        load_batch(file_names, image_locations, quantities, description, checkmarked,
                   materials, batch_name_list, batch_index_val, BATCH=BATCH_TO)
        file_names_TO = file_names
        for TO in file_names_TO:
            if TO == name:
                self.returns[bar] = 'File Exists'
                return
        clear_batches()
        load_batch(file_names, image_locations, quantities, description, checkmarked,
                   materials, batch_name_list, batch_index_val, BATCH=BATCH_FROM)

        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
        Data_JSON_Contents[0][BATCH_FROM].pop(index)
        Data_JSON_Contents[0][BATCH_TO].append({
            'fileName': [file_names[index]],
            'imgLoc': [image_locations[index]],
            'quantity': [int(quantities[index])],
            'description': [description[index]],
            'checked': [checkmarked[index]],
            'material': [materials[index]]
        })
        with open(Data_JSON, mode='w+', encoding='utf-8') as file:
            json.dump(Data_JSON_Contents, file,
                      ensure_ascii=True)
        sort_data(BATCH_TO)
        self.returns[bar] = 'True'

    def move_all_parts_Thread(self, bar, BATCH_FROM, BATCH_TO):
        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
        clear_batches()
        load_batch(file_names, image_locations, quantities, description, checkmarked,
                   materials, batch_name_list, batch_index_val, BATCH=BATCH_FROM)
        for index, _ in enumerate(file_names):
            Data_JSON_Contents[0][BATCH_TO].append({
                'fileName': [file_names[index]],
                'imgLoc': [image_locations[index]],
                'quantity': [int(quantities[index])],
                'description': [description[index]],
                'checked': [checkmarked[index]],
                'material': [materials[index]]
            })
        clear_batches()
        load_batch(file_names, image_locations, quantities, description, checkmarked,
                   materials, batch_name_list, batch_index_val, BATCH=BATCH_FROM)
        for _ in file_names:
            Data_JSON_Contents[0][BATCH_FROM].pop(0)
        with open(Data_JSON, mode='w+', encoding='utf-8') as file:
            json.dump(Data_JSON_Contents, file,
                      ensure_ascii=True)
        sort_data(BATCH_TO)
        self.returns[bar] = 'True'

    # --------------------------------------------

    def saveLineEdit(self, textBox, index, isInt, BATCH):
        # return
        self.setCursor(Qt.BusyCursor)
        if isInt == 'Int':
            text = textBox.text()
        elif isInt == 'Str':
            text = textBox.toPlainText()
        elif isInt == 'Chk':
            text = textBox.isChecked()
        elif isInt == 'Combo':
            text = textBox.currentText()
        elif isInt == 'ComboEdit':
            text = textBox.text()
        t = threading.Thread(target=self.saveLineEditThreading, args=(
            'isdone', text, index, isInt, BATCH))
        t.start()
        t.join()
        if self.returns['isdone'] == 'True':
            self.unsetCursor()

    def saveLineEditThreading(self, bar, text, index, isInt, BATCH_NAME):
        clear_batches()
        load_batch(file_names, image_locations, quantities, description, checkmarked,
                   materials, batch_name_list, batch_index_val, BATCH=BATCH_NAME)
        with open(Data_JSON) as file:
            Data_JSON_Contents = json.load(file)
        Data_JSON_Contents[0][BATCH_NAME].pop(index)
        if isInt == 'Int':
            Data_JSON_Contents[0][BATCH_NAME].append({
                'fileName': [file_names[index]],
                'imgLoc': [image_locations[index]],
                'quantity': [int(text)],
                'description': [description[index]],
                'checked': [checkmarked[index]],
                'material': [materials[index]]
            })
        elif isInt == 'Str':
            Data_JSON_Contents[0][BATCH_NAME].append({
                'fileName': [file_names[index]],
                'imgLoc': [image_locations[index]],
                'quantity': [int(quantities[index])],
                'description': [text],
                'checked': [checkmarked[index]],
                'material': [materials[index]]
            })
        elif isInt == 'Chk':
            Data_JSON_Contents[0][BATCH_NAME].append({
                'fileName': [file_names[index]],
                'imgLoc': [image_locations[index]],
                'quantity': [int(quantities[index])],
                'description': [description[index]],
                'checked': [str(text)],
                'material': [materials[index]]
            })
        elif 'Combo' in isInt or 'ComboEdit' in isInt:
            Data_JSON_Contents[0][BATCH_NAME].append({
                'fileName': [file_names[index]],
                'imgLoc': [image_locations[index]],
                'quantity': [int(quantities[index])],
                'description': [description[index]],
                'checked': [checkmarked[index]],
                'material': [text]
            })
        with open(Data_JSON, mode='w+', encoding='utf-8') as file:
            json.dump(Data_JSON_Contents, file,
                      ensure_ascii=True)
        sort_data(BATCH_NAME)
        self.returns[bar] = 'True'

    def search(self):
        if self.last_search_text != self.txtSearch.text():
            self.reloadListUI()
        self.last_search_text = self.txtSearch.text()

    def btnsearch(self):
        if self.txtSearch.text() != '' and self.last_search_text != self.txtSearch.text():
            self.reloadListUI()
        self.last_search_text = self.txtSearch.text()

    def center(self):
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(
            QApplication.desktop().cursor().pos())
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
        self.setTabChangesFocus(True)
        self.textChanged.connect(self._handle_text_changed)

    def focusInEvent(self, event):
        super(TextEdit, self).focusInEvent(event)
        self.receivedFocus.emit()

    def focusOutEvent(self, event):
        if self._changed:
            self.editingFinished.emit()
        super(TextEdit, self).focusOutEvent(event)

    def _handle_text_changed(self):
        self._changed = True

    def setTextChanged(self, state=True):
        self._changed = state

    def setHtml(self, html):
        QtGui.QTextEdit.setHtml(self, html)
        self._changed = False


class QPushButtonQLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, parent=None):
        QLabel.__init__(self, parent)

    def mousePressEvent(self, ev):
        self.clicked.emit()


class SearchButtonLineEdit(QLineEdit):
    buttonClicked = QtCore.pyqtSignal(bool)

    def __init__(self, icon_file, parent=None):
        super(SearchButtonLineEdit, self).__init__(parent)

        self.button = QToolButton(self)
        self.button.setIcon(QIcon(icon_file))
        self.button.setStyleSheet('border: 0px; padding: 0px;')
        self.button.setCursor(Qt.PointingHandCursor)
        self.button.clicked.connect(self.buttonClicked.emit)
        self.button.setFixedSize(28, 28)


class CheckDirThread(QThread):
    sig = pyqtSignal()

    def __init__(self):
        QThread.__init__(self)

    def run(self):
        while True:
            if not os.listdir('Capture/'):
                self.sig.emit()
                break


class QImageViewer(QMainWindow):
    def __init__(self, directory_to_open):
        super().__init__()

        self.path = directory_to_open

        self.printer = QPrinter()
        self.scaleFactor = 0.0

        self.imageLabel = QLabel()
        self.imageLabel.setBackgroundRole(QPalette.Base)
        self.imageLabel.setSizePolicy(
            QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.imageLabel.setAlignment(Qt.AlignCenter)
        self.imageLabel.setScaledContents(True)

        self.scrollArea = QScrollArea()
        self.scrollArea.setBackgroundRole(QPalette.Dark)
        self.scrollArea.setWidget(self.imageLabel)
        self.scrollArea.setVisible(False)
        self.scrollArea.setAlignment(Qt.AlignCenter)

        self.setCentralWidget(self.scrollArea)

        self.createActions()
        self.createMenus()

        self.setWindowTitle(self.path)
        self.resize(800, 600)

        pixmap = QPixmap(self.path)
        pixmap = pixmap.scaled(pixmap.width(), pixmap.height(
        ), Qt.KeepAspectRatio, Qt.FastTransformation)
        self.imageLabel.setPixmap(pixmap)
        self.imageLabel.adjustSize()
        self.scrollArea.setVisible(True)
        self.printAct.setEnabled(False)
        self.fitToWindowAct.setEnabled(True)
        self.updateActions()

        if not self.fitToWindowAct.isChecked():
            self.imageLabel.adjustSize()
        self.scaleFactor = 0.5
        self.scaleImage(self.scaleFactor)
        self.start_thread()

    def start_thread(self):
        self.setCursor(Qt.BusyCursor)
        self.threads = []
        converter = CheckDirThread()
        converter.sig.connect(self.on_data_ready)
        self.threads.append(converter)
        converter.start()

    def on_data_ready(self):
        self.printAct.setEnabled(True)
        self.unsetCursor()

    def print_(self):
        dialog = QPrintDialog(self.printer, self)
        onlyfiles = next(os.walk('Print/'))[2]
        onlyfiles.sort(key=natsort_key)
        if dialog.exec_():
            for picture in onlyfiles:
                pixmap = QPixmap(os.path.dirname(
                    os.path.abspath(__file__)) + '/Print/' + picture)
                pixmap = pixmap.scaled(pixmap.width(), pixmap.height(
                ), Qt.KeepAspectRatio, Qt.FastTransformation)

                self.imageLabel.setPixmap(pixmap)
                self.imageLabel.adjustSize()

                painter = QPainter(self.printer)
                rect = painter.viewport()
                size = self.imageLabel.pixmap().size()
                size.scale(rect.size(), Qt.KeepAspectRatio)
                painter.setViewport(rect.x(), rect.y(),
                                    size.width(), size.height())
                painter.setWindow(self.imageLabel.pixmap().rect())
                painter.drawPixmap(0, 0, self.imageLabel.pixmap())
                os.remove(os.path.dirname(os.path.abspath(
                    __file__)) + '/Print/' + picture)

                loop = QEventLoop()
                QTimer.singleShot(1000, loop.quit)
                loop.exec_()

            pixmap = QPixmap(self.path)
            pixmap = pixmap.scaled(pixmap.width(), pixmap.height(
            ), Qt.KeepAspectRatio, Qt.FastTransformation)
            self.imageLabel.setPixmap(pixmap)
            self.imageLabel.adjustSize()
            clear_folders(['Capture', 'Print'])
        self.scaleImage(self.scaleFactor)

    def zoomIn(self):
        self.scaleImage(1.25)

    def zoomOut(self):
        self.scaleImage(0.8)

    def normalSize(self):
        self.scaleFactor = 0.5

    def fitToWindow(self):
        fitToWindow = self.fitToWindowAct.isChecked()
        self.scrollArea.setWidgetResizable(fitToWindow)
        if not fitToWindow:
            self.normalSize()

        self.updateActions()

    def createActions(self):
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

    def createMenus(self):
        self.fileMenu = QMenu("&File", self)
        self.fileMenu.addAction(self.printAct)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.exitAct)

        self.viewMenu = QMenu("&View", self)
        self.viewMenu.addAction(self.zoomInAct)
        self.viewMenu.addAction(self.zoomOutAct)
        self.viewMenu.addAction(self.normalSizeAct)
        self.viewMenu.addSeparator()
        self.viewMenu.addAction(self.fitToWindowAct)

        self.menuBar().addMenu(self.fileMenu)
        self.menuBar().addMenu(self.viewMenu)

    def updateActions(self):
        self.zoomInAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.zoomOutAct.setEnabled(not self.fitToWindowAct.isChecked())
        self.normalSizeAct.setEnabled(not self.fitToWindowAct.isChecked())

    def scaleImage(self, factor):
        self.scaleFactor *= factor
        self.imageLabel.resize(
            self.scaleFactor * self.imageLabel.pixmap().size())

        self.adjustScrollBar(self.scrollArea.horizontalScrollBar(), factor)
        self.adjustScrollBar(self.scrollArea.verticalScrollBar(), factor)

        self.zoomInAct.setEnabled(self.scaleFactor < 1.0)
        self.zoomOutAct.setEnabled(self.scaleFactor > 0.3)

    def adjustScrollBar(self, scrollBar, factor):
        scrollBar.setValue(int(factor * scrollBar.value()
                               + ((factor - 1) * scrollBar.pageStep() / 2)))


class aboutwindowUI(QDialog):

    def __init__(self, parent=None):
        super(aboutwindowUI, self).__init__(parent)
        uic.loadUi('UI/aboutwindow.ui', self)
        self.setWindowTitle("About")
        self.setWindowIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_FileDialogInfoView')))
        self.icon = self.findChild(QLabel, 'lblIcon')
        self.icon.setFixedSize(100, 100)
        pixmap = QPixmap('icon.png')
        myScaledPixmap = pixmap.scaled(self.icon.size(), Qt.KeepAspectRatio)
        self.icon.setPixmap(myScaledPixmap)
        self.lisenceText = self.findChild(QLabel, 'label_2')
        with open('LICENSE', 'r') as f:
            self.lisenceText.setText(f.read())
        self.btnClose = self.findChild(QPushButton, 'btnClose')
        self.btnClose.setIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_DialogCloseButton')))
        self.btnClose.clicked.connect(self.close)
        self.setFixedSize(600, 370)
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


def load_batches(*args):
    global Data_JSON_Contents
    for j in args:
        j.clear()
    with open(Data_JSON) as file:
        Data_JSON_Contents = json.load(file)
        for info in Data_JSON_Contents:
            for batch in info:
                if batch != 'NON_BATCH':
                    args[0].append(batch)
        args[0].append('NON_BATCH')


def merge(*args): return [(args[0][i], args[1][i], args[2][i],
                           args[3][i], args[4][i], args[5][i]) for i in range(len(args[0]))]


def clear_batches(*args):
    file_names.clear()
    image_locations.clear()
    quantities.clear()
    description.clear()
    checkmarked.clear()
    materials.clear()
    batch_name_list.clear()
    batch_index_val.clear()


def sort_data(BATCH_NAME):
    # save data to JSON file
    with open(Data_JSON) as file:
        Data_JSON_Contents = json.load(file)
        temp_file_names = []
        temp_image_locations = []
        temp_quantities = []
        temp_description = []
        temp_checkmarked = []
        temp_materials = []
        for item in Data_JSON_Contents[0][BATCH_NAME]:
            temp_file_names.append(item['fileName'][0])
            temp_image_locations.append(item['imgLoc'][0])
            temp_quantities.append(item['quantity'][0])
            temp_description.append(item['description'][0])
            temp_checkmarked.append(item['checked'][0])
            temp_materials.append(item['material'][0])

        merged = sorted(merge(temp_file_names, temp_image_locations, temp_quantities,
                              temp_description, temp_checkmarked, temp_materials), key=natsort_key)

        for i, _ in enumerate(temp_file_names):
            Data_JSON_Contents[0][BATCH_NAME].pop(0)
            Data_JSON_Contents[0][BATCH_NAME].append({
                'fileName': [merged[i][0]],
                'imgLoc': [merged[i][1]],
                'quantity': [int(merged[i][2])],
                'description': [merged[i][3]],
                'checked': [merged[i][4]],
                'material': [merged[i][5]]
            })
        with open(Data_JSON, mode='w+', encoding='utf-8') as file:
            json.dump(Data_JSON_Contents, file,
                      ensure_ascii=True)


def clear_folders(folders):
    for folder in folders:
        for filename in os.listdir(folder):
            file_path = os.path.join(folder, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))


def load_batch(*args, BATCH):
    with open(Data_JSON) as file:
        try:
            Data_JSON_Contents = json.load(file)
            for _, info in enumerate(Data_JSON_Contents):
                for index, info1 in enumerate(info[BATCH]):
                    args[6].append(BATCH)
                    args[7].append(index)
                    for name in info1['fileName']:
                        args[0].append(name)
                    for path in info1['imgLoc']:
                        args[1].append(path)
                    for quan in info1['quantity']:
                        args[2].append(quan)
                    for disc in info1['description']:
                        args[3].append(disc)
                    for chk in info1['checked']:
                        args[4].append(chk)
                    for mat in info1['material']:
                        args[5].append(mat)
        except Exception as e:
            print(e)

def get_all_file_paths(directory): 
    file_paths = [] 
    for root, directories, files in os.walk(directory): 
        for filename in files:  
            filepath = os.path.join(root, filename) 
            file_paths.append(filepath) 
  
    # returning all file paths 
    return file_paths         

if __name__ == '__main__':
    # if images directory doesn't exist we create it
    if not os.path.exists('Images'): os.makedirs('Images')
    if not os.path.exists('Print'): os.makedirs('Print')
    if not os.path.exists('Capture'): os.makedirs('Capture')
    if not os.path.exists('Batches'): os.makedirs('Batches')
    if not os.path.exists('Backups'): os.makedirs('Backups')
    # if data.json file doesn't exist, we create it
    if not os.path.isfile(Data_JSON):
        with open(Data_JSON, 'w+') as f:
            f.write('[{"NON_BATCH":[]}]')
    clear_folders(['Capture', 'Print'])
    # Load data file
    load_batches(BATCHES)
    SAVED_DATA_JSON_FILES = os.listdir('Batches/')
    
    parser = argparse.ArgumentParser(description = 'This application allows converting DXF to PNG')
    parser.add_argument('--cli',
            help = 'Runs the application in Command Line Interface (CLI)',
            action = 'store_true')
    args = parser.parse_args()
    if (args.cli):
        pass
    else:
        # start GUI
        app = QApplication(sys.argv)
        app.setStyle('Fusion')
        app.setPalette(QApplication.style().standardPalette())
        palette = QPalette()
        palette.setColor(QPalette.ButtonText, QColor(30, 30, 30))
        palette.setColor(QPalette.Text, QColor(30, 30, 30))
        palette.setColor(QPalette.Window, QColor(255, 255, 255))
        palette.setColor(QPalette.AlternateBase, QColor(255, 255, 255))
        palette.setColor(QPalette.Background, QColor(255, 255, 255))
        palette.setColor(QPalette.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.Shadow, QColor(255, 255, 255))
        palette.setColor(QPalette.Base, QColor(255, 255, 255))
        app.setPalette(palette)
        window = mainwindowUI()
        sys.exit(app.exec_())
