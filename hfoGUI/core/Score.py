from pyqtgraph.Qt import QtGui, QtCore
from core.GUI_Utils import background, center, find_consec
import os, time, json, functools
from scipy.signal import hilbert
import numpy as np
from core.Tint_Matlab import detect_peaks
from core.GUI_Utils import Worker
import pandas as pd
import core.filtering as filt


class TreeWidgetItem(QtGui.QTreeWidgetItem):
    """This subclass was created so that the __lt__ method could be overwritten so that the numerical data values
    are treated correctly (not as strings)"""
    def __init__(self, parent=None):
        QtGui.QTreeWidgetItem.__init__(self, parent)

    def __lt__(self, otherItem):
        column = self.treeWidget().sortColumn()
        try:
            return float(self.text(column)) < float(otherItem.text(column))
        except ValueError:
            return self.text(column) < otherItem.text(column)


class AddItemSignal(QtCore.QObject):
    """This is a signal was created so that we could add QTreeWidgetItems
    from the main thread since it did not like that we were adding EOIs
    from a thread"""
    childAdded = QtCore.pyqtSignal(object)


class custom_signal(QtCore.QObject):
    """This method will contain the signal that will allow for the linear region selector to be
    where the current score/EOI is so the user can change if they want"""

    set_lr_signal = QtCore.pyqtSignal(str, str)


class ScoreWindow(QtGui.QWidget):
    '''This is the window that will pop up to score the '''

    def __init__(self, main, settings):
        super(ScoreWindow, self).__init__()

        self.AddItemSignal = AddItemSignal()
        self.AddItemSignal.childAdded.connect(self.add_item)

        self.mainWindow = main

        self.customSignals = custom_signal()
        self.customSignals.set_lr_signal.connect(self.mainWindow.set_lr)

        self.settingsWindow = settings

        self.initialize_attributes()

        background(self)
        width = self.deskW / 6
        height = self.deskH / 1.5

        self.setWindowTitle(
            os.path.splitext(os.path.basename(__file__))[0] + " - Score Window")  # sets the title of the window

        main_location = main.frameGeometry().getCoords()

        self.setGeometry(main_location[2], main_location[1]+30, width, height)

        tabs = QtGui.QTabWidget()
        score_tab = QtGui.QWidget()
        eoi_tab = QtGui.QWidget()

        # ----------------------- score filename widget - score tab ----------------------------------------

        self.save_score_btn = QtGui.QPushButton('Save Scores', self)
        self.save_score_btn.clicked.connect(self.saveScores)

        self.load_score_btn = QtGui.QPushButton('Load Scores', self)
        self.load_score_btn.clicked.connect(self.loadScores)

        score_filename_btn_layout = QtGui.QHBoxLayout()
        score_filename_btn_layout.addWidget(self.load_score_btn)
        score_filename_btn_layout.addWidget(self.save_score_btn)

        score_filename_label = QtGui.QLabel('Score Filename:')
        self.score_filename = QtGui.QLineEdit()
        self.score_filename.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.score_filename.setText("Please add a source!")

        score_filename_layout = QtGui.QHBoxLayout()
        score_filename_layout.addWidget(score_filename_label)
        score_filename_layout.addWidget(self.score_filename)


        scorer_filename_label = QtGui.QLabel('Scorer:')
        self.scorer = QtGui.QLineEdit()

        scorer_layout = QtGui.QHBoxLayout()
        scorer_layout.addWidget(scorer_filename_label)
        scorer_layout.addWidget(self.scorer)

        source_label = QtGui.QLabel("Source:")
        self.source = QtGui.QComboBox()
        self.source.setEditable(True)
        self.source.lineEdit().setReadOnly(True)
        self.source.lineEdit().setAlignment(QtCore.Qt.AlignHCenter)
        self.source.currentIndexChanged.connect(self.changeSources)
        self.source.setSizePolicy(QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))
        self.source.addItem("None")
        source_layout = QtGui.QHBoxLayout()
        source_layout.addWidget(source_label)
        source_layout.addWidget(self.source)

        # -------------------------- scores widget --------------------------------------

        self.scores = QtGui.QTreeWidget()
        self.scores.setSortingEnabled(True)
        self.scores.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.scores.customContextMenuRequested.connect(functools.partial(self.openMenu, 'score'))

        self.scores.itemSelectionChanged.connect(functools.partial(self.changeEventText, 'score'))

        self.score_headers = {'ID#:': 0, "Score:": 1, "Start Time(ms):": 2, "Stop Time(ms):": 3, "Scorer:": 4,
                              "Settings File:": 5}

        for key, value in self.score_headers.items():
            self.scores.headerItem().setText(value, key)
            if 'Start Time' in key:
                self.scores.sortItems(value, QtCore.Qt.AscendingOrder)

        # ----------------------- scoring widgets -------------------------

        self.score = QtGui.QComboBox()
        self.score.setEditable(True)
        self.score.lineEdit().setReadOnly(True)
        self.score.lineEdit().setAlignment(QtCore.Qt.AlignHCenter)
        self.score.setSizePolicy(QtGui.QSizePolicy(
                        QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))

        score_values = ['None', 'Spike', 'Theta', 'Gamma Low', 'Gamma High', 'Ripple', 'Fast Ripple', 'Sharp Wave Ripple',
                        'Artifact',
                        'Other']

        self.id_abbreviations = {'manual': 'MAN', 'hilbert': 'HIL', 'unknown': 'UNK'}

        for score in score_values:
            self.score.addItem(score)

        score_label = QtGui.QLabel("Score:")

        score_layout = QtGui.QHBoxLayout()
        score_layout.addWidget(score_label)
        score_layout.addWidget(self.score)

        # ------------------------------button layout --------------------------------------
        self.hide_btn = QtGui.QPushButton('Hide', self)
        self.add_btn = QtGui.QPushButton('Add Score', self)
        self.add_btn.clicked.connect(self.addScore)
        self.update_btn = QtGui.QPushButton('Update Selected Scores')
        self.update_btn.clicked.connect(self.updateScores)
        self.delete_btn = QtGui.QPushButton('Delete Selected Scores', self)
        self.delete_btn.clicked.connect(self.deleteScores)

        btn_layout = QtGui.QHBoxLayout()

        for button in [self.add_btn, self.update_btn, self.delete_btn, self.hide_btn]:
            btn_layout.addWidget(button)
        # ------------------ layout ------------------------------

        layout_order = [score_filename_btn_layout, score_filename_layout,  scorer_layout, self.scores, score_layout,
                        btn_layout]

        layout_score = QtGui.QVBoxLayout()
        for order in layout_order:
            if 'Layout' in order.__str__():
                layout_score.addLayout(order)
            else:
                layout_score.addWidget(order)

        # ------- EOI widgets -----------

        eoi_filename_label = QtGui.QLabel('EOI Filename:')
        self.eoi_filename = QtGui.QLineEdit()
        self.eoi_filename.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.eoi_filename.setText("Please add a source!")

        eoi_filename_layout = QtGui.QHBoxLayout()
        eoi_filename_layout.addWidget(eoi_filename_label)
        eoi_filename_layout.addWidget(self.eoi_filename)

        self.save_eoi_btn = QtGui.QPushButton("Save EOI's")
        self.save_eoi_btn.clicked.connect(self.saveAutomaticEOIs)
        eoi_button_layout = QtGui.QHBoxLayout()

        self.load_eois = QtGui.QPushButton("Load EOI's")
        self.load_eois.clicked.connect(self.loadAutomaticEOIs)

        eoi_button_layout.addWidget(self.load_eois)
        eoi_button_layout.addWidget(self.save_eoi_btn)

        self.EOI_score = QtGui.QComboBox()
        self.EOI_score.setEditable(True)
        self.EOI_score.lineEdit().setReadOnly(True)
        self.EOI_score.lineEdit().setAlignment(QtCore.Qt.AlignHCenter)
        self.EOI_score.setSizePolicy(QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))

        for score in score_values:
            self.EOI_score.addItem(score)

        EOI_score_label = QtGui.QLabel("Score:")

        EOI_score_layout = QtGui.QHBoxLayout()
        EOI_score_layout.addWidget(EOI_score_label)
        EOI_score_layout.addWidget(self.EOI_score)

        eoi_method_label = QtGui.QLabel("EOI Detection Method:")
        self.eoi_method = QtGui.QComboBox()
        self.eoi_method.currentIndexChanged.connect(self.setEOIfilename)
        methods = ['Hilbert']

        events_detected_label = QtGui.QLabel('Events Detected:')
        self.events_detected = QtGui.QLineEdit()

        events_detected_layout = QtGui.QHBoxLayout()
        events_detected_layout.addWidget(events_detected_label)
        events_detected_layout.addWidget(self.events_detected)
        self.events_detected.setText('0')
        self.events_detected.setEnabled(0)

        for method in methods:
            self.eoi_method.addItem(method)

        eoi_method_layout = QtGui.QHBoxLayout()
        eoi_method_layout.addWidget(eoi_method_label)
        eoi_method_layout.addWidget(self.eoi_method)

        eoi_parameter_layout = QtGui.QHBoxLayout()
        eoi_parameter_layout.addLayout(eoi_method_layout)
        eoi_parameter_layout.addLayout(events_detected_layout)

        self.EOI = QtGui.QTreeWidget()
        self.EOI.setSortingEnabled(True)
        self.EOI.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.EOI.customContextMenuRequested.connect(functools.partial(self.openMenu, 'EOI'))
        self.EOI_headers = {'ID#:': 0, "Start Time(ms):": 1, "Stop Time(ms):": 2, 'Settings File:': 3}

        for key, value in self.EOI_headers.items():
            self.EOI.headerItem().setText(value, key)
            if 'Start Time' in key:
                self.EOI.sortItems(value, QtCore.Qt.AscendingOrder)

        self.EOI.itemSelectionChanged.connect(functools.partial(self.changeEventText, 'EOI'))

        # ----- EOI tab buttons ---------------
        self.update_eoi_region = QtGui.QPushButton("Update EOI Region")
        self.update_eoi_region.setToolTip("This will modify the times based on the current selected window")
        self.update_eoi_region.clicked.connect(self.updateEOIRegion)

        self.eoi_hide = QtGui.QPushButton("Hide")
        self.find_eoi_btn = QtGui.QPushButton("Find EOI's")
        self.find_eoi_btn.clicked.connect(self.findEOIs)
        self.delete_eoi_btn = QtGui.QPushButton("Remove Selected EOI")
        self.delete_eoi_btn.clicked.connect(self.deleteEOI)

        self.add_eoi_btn = QtGui.QPushButton("Add Selected EOI to Score")
        self.add_eoi_btn.clicked.connect(self.addEOI)

        btn_layout = QtGui.QHBoxLayout()
        for btn in [self.find_eoi_btn, self.add_eoi_btn, self.update_eoi_region, self.delete_eoi_btn, self.eoi_hide]:
            btn_layout.addWidget(btn)

        layout_eoi = QtGui.QVBoxLayout()

        for item in [eoi_button_layout, eoi_filename_layout, eoi_parameter_layout, self.EOI, EOI_score_layout, btn_layout]:
            if 'Layout' in item.__str__():
                layout_eoi.addLayout(item)
            else:
                layout_eoi.addWidget(item)

        score_tab.setLayout(layout_score)

        eoi_tab.setLayout(layout_eoi)

        tabs.addTab(score_tab, 'Score')
        tabs.addTab(eoi_tab, 'Automatic Detection')

        window_layout = QtGui.QVBoxLayout()
        for item in [source_layout, tabs]:
            if 'Layout' in item.__str__():
                window_layout.addLayout(item)
            else:
                window_layout.addWidget(item)
                # layout_score.addStretch(1)

        self.hilbert_thread = QtCore.QThread()
        self.setLayout(window_layout)

    def initialize_attributes(self):
        self.IDs = []

    def openSettings(self, index, source):

        if 'score' in source:
            for key, val in self.score_headers.items():
                if 'Settings' in key:
                    break
        else:
            for key, val in self.EOI_headers.items():
                if 'Settings' in key:
                    break

        settings_filename = index[val].data()
        if settings_filename != '' or settings_filename != 'N/A':

            if os.path.exists(settings_filename):
                self.setting_viewer_window = SettingsViewer(settings_filename)

    def copySettings(self, index, source):
        if 'score' in source:
            for key, val in self.score_headers.items():
                if 'Settings' in key:
                    break
        else:
            for key, val in self.EOI_headers.items():
                if 'Settings' in key:
                    break

        settings_filename = index[val].data()
        if settings_filename != '' or settings_filename != 'N/A':
            # pyperclip.copy(settings_filename)
            cb = QtGui.QApplication.clipboard()
            cb.clear(mode=cb.Clipboard)
            cb.setText(settings_filename, mode=cb.Clipboard)

    def openMenu(self, source, position):

        menu = QtGui.QMenu()

        if 'score' in source:
            indexes = self.scores.selectedIndexes()

            menu.addAction("Open Settings File", functools.partial(self.openSettings, indexes, source))
            menu.addAction("Copy Settings Filepath", functools.partial(self.copySettings, indexes, source))

            menu.exec_(self.scores.viewport().mapToGlobal(position))
        else:
            indexes = self.EOI.selectedIndexes()

            menu.addAction("Open Settings File", functools.partial(self.openSettings, indexes, source))
            menu.addAction("Copy Settings Filepath", functools.partial(self.copySettings, indexes, source))

            menu.exec_(self.EOI.viewport().mapToGlobal(position))

    def addScore(self):
        if self.mainWindow.score_x1 is None or self.mainWindow.score_x2 is None:
            return

        if self.scorer.text() == '':
            self.mainWindow.choice = ''
            self.mainWindow.ErrorDialogue.myGUI_signal.emit("NoScorer")

            while self.mainWindow.choice == '':
                time.sleep(0.1)
            return

        # new_item = QtGui.QTreeWidgetItem()
        new_item = TreeWidgetItem()
        id = self.createID('Manual')
        self.IDs.append(id)

        for key, value in self.score_headers.items():
            if 'ID' in key:
                new_item.setText(value, id)
            elif 'Score:' in key:
                new_item.setText(value, self.score.currentText())
            elif 'Start' in key:
                new_item.setText(value, str(self.mainWindow.score_x1))
            elif 'Stop' in key:
                new_item.setText(value, str(self.mainWindow.score_x2))
            elif 'Settings File' in key:
                # there is no settings file involved in manual detection
                new_item.setText(value, 'N/A')
            elif 'Scorer' in key:
                new_item.setText(value, self.scorer.text())

        self.scores.addTopLevelItem(new_item)

    def add_item(self, item):
        """This is a method was created so that we could add QTreeWidgetItems
            from the main thread since it did not like that we were adding EOIs
            from a thread"""
        self.EOI.addTopLevelItem(item)

    def createID(self, source):
        """This method will create an ID for the newly added Score"""
        source = source.lower()

        existing_IDs = self.existingID(source)  # get the IDs with that existing source

        ID_numbers = np.asarray([int(ID[3:]) for ID in existing_IDs]).flatten()

        if len(ID_numbers) != 0:
            return '%s%d' % (self.id_abbreviations[source], np.setdiff1d(np.arange(1, len(existing_IDs)+2), ID_numbers)[0])
        else:
            # there are no ID's,
            return '%s%d' % (self.id_abbreviations[source], 1)

    def existingID(self, source):

        source = source.lower()

        abbreviation = self.id_abbreviations[source]

        '''
        # this method involves iterating which will be more time consuming, instead I'll keep a list of the values
        # root = self.scores.invisibleRootItem()
        iterator = QtGui.QTreeWidgetItemIterator(self.scores)

        

        ID = []
        while iterator.value():
            item = iterator.value()
            current_id = item.data(0, 0)
            if abbreviation in current_id:
                ID.append(current_id)

            iterator += 1
        '''

        ID = [value for value in self.IDs if abbreviation in value]

        return ID

    def deleteScores(self):
        '''deletes the selected scores in the Scores Window\'s TreeWidget'''
        root = self.scores.invisibleRootItem()

        for key, value in self.score_headers.items():
            if 'ID' in key:
                id_value = value
                break

        for item in self.scores.selectedItems():
            ID = item.data(id_value, 0)
            self.IDs.pop(self.IDs.index(ID))  # remove the id from the list of IDs
            (item.parent() or root).removeChild(item)

    def updateScores(self):
        '''updates the selected scores in the Score Window\'s TreeWidget'''
        root = self.scores.invisibleRootItem()

        for key, value in self.score_headers.items():
            if 'Score:' in key:
                score_value = value
            elif 'Start Time' in key:
                start_value = value
            elif 'Stop Time' in key:
                stop_value = value

        if hasattr(self.mainWindow, 'lr'):
            x1, x2 = self.mainWindow.lr.getRegion()
            for item in self.scores.selectedItems():
                item.setText(score_value, self.score.currentText())
                item.setText(start_value, str(x1))
                item.setText(stop_value, str(x2))
        else:
            for item in self.scores.selectedItems():
                item.setText(score_value, self.score.currentText())

    def updateEOIRegion(self):
        root = self.EOI.invisibleRootItem()

        for key, value in self.EOI_headers.items():
            if 'Start Time' in key:
                start_value = value
            elif 'Stop Time' in key:
                stop_value = value

        if hasattr(self.mainWindow, 'lr'):
            x1, x2 = self.mainWindow.lr.getRegion()
            for item in self.EOI.selectedItems():
                item.setText(start_value, str(x1))
                item.setText(stop_value, str(x2))
        else:
           pass

    def loadScores(self):

        # choose the filename
        save_filename = self.score_filename.text()

        if 'Please add a source!' in save_filename:
            return

        save_filename, save_fileextension = QtGui.QFileDialog.getOpenFileName(self, 'Load Scores',
                                                          save_filename,
                                                          'Text Files (*.txt)')
        if save_filename == '':
            return

        self.score_filename.setText(save_filename)

        if os.path.exists(save_filename):
            df = pd.read_csv(save_filename, delimiter='\t')
        else:
            self.mainWindow.choice = ''
            self.mainWindow.ErrorDialogue.myGUI_signal.emit("ScoreFileExistError:%s" % save_filename)

            while self.mainWindow.choice == '':
                time.sleep(0.1)

            return

        # add the scores

        N = len(df)

        # find the IDs of any existing EOIs
        iterator = QtGui.QTreeWidgetItemIterator(self.scores)

        score_IDs = []
        while iterator.value():
            item = iterator.value()
            score_IDs.append(item.data(0, 0))
            iterator += 1

        self.scores.clear()
        [self.IDs.pop(self.IDs.index(ID)) for ID in score_IDs]  # remove the id from the list of IDs

        ids_exist = any('ID' in column for column in df.columns)
        scorer_exists = any('Scorer' in column for column in df.columns)
        score_settings_file_exists = any('Settings File' in column for column in df.columns)

        for key, value in self.score_headers.items():
            if 'ID' in key:
                id_value = value

            elif 'Scorer' in key:
                scorer_value = value

            elif 'Settings File' in key:
                settings_value = value

            elif 'Start' in key:
                start_value = value

            elif 'Score:' in key:
                score_value = value

        for score_index in range(N):
            # item = QtGui.QTreeWidgetItem()
            item = TreeWidgetItem()

            if not ids_exist:
                ID = self.createID('Unknown')
                self.IDs.append(ID)
                item.setText(id_value, ID)

            if not scorer_exists:
                item.setText(scorer_value, 'Unknown')

            if not score_settings_file_exists:
                item.setText(settings_value, 'N/A')

            for column in df.columns:

                if 'Unnamed' in column:
                    continue

                for key, value in self.score_headers.items():
                    if key == column:
                        if 'ID' in key:
                            ID = df[column][score_index]
                            self.IDs.append(ID)
                            item.setText(value, ID)

                        else:
                            item.setText(value, str(df[column][score_index]))

                    # these next statements are for the older files
                    elif 'Score:' in column and 'Score:' in key:
                        item.setText(value, str(df[column][score_index]))

                    elif 'Scorer:' in column and 'Scorer:' in key:
                        item.setText(value, str(df[column][score_index]))

                    elif 'Start' in column and 'Start' in key:
                        item.setText(value, str(df[column][score_index]))

                    elif 'Stop' in column and 'Stop' in key:
                        item.setText(value, str(df[column][score_index]))

            self.scores.addTopLevelItem(item)

            self.scores.sortItems(start_value, QtCore.Qt.AscendingOrder)

    def saveScores(self):
        """This method will save the scores into a text file"""
        # iterate through each item

        # choose the filename
        save_filename = self.score_filename.text()

        if 'Please add a source!' in save_filename:
            return

        save_filename, save_file_extension = QtGui.QFileDialog.getSaveFileName(self, 'Save Scores',
                                                          save_filename,
                                                          'Text Files (*.txt)')

        if save_filename == '':
            return

        self.score_filename.setText(save_filename)

        scores = []
        start_times = []
        stop_times = []
        ids = []
        scorer = []

        for key, value in self.score_headers.items():
            if 'Score:' in key:
                score_value = value
            elif 'Start' in key:
                start_value = value
            elif 'Stop' in key:
                stop_value = value
            elif 'ID' in key:
                id_value = value
            elif 'Scorer:' in key:
                scorer_value = value

        for item_count in range(self.scores.topLevelItemCount()):
            item = self.scores.topLevelItem(item_count)

            ids.append(item.data(id_value, 0))
            scores.append(item.data(score_value, 0))
            start_times.append(item.data(start_value, 0))
            stop_times.append(item.data(stop_value, 0))
            scorer.append(item.data(scorer_value, 0))

        data_dict = {}
        for key, value in self.score_headers.items():
            if 'ID' in key:
                data_dict[key] = ids

            elif 'Score:' in key:
                data_dict[key] = pd.Series(scores)

            elif 'Start' in key:
                data_dict[key] = pd.Series(start_times)

            elif 'Stop' in key:
                data_dict[key] = pd.Series(stop_times)

            elif 'Scorer' in key:
                data_dict[key] = pd.Series(scorer)

        df = pd.DataFrame(data_dict)

        # make the directory name if it does not exists already
        if not os.path.exists(os.path.dirname(save_filename)):
            os.makedirs(os.path.dirname(save_filename))

        df.to_csv(save_filename, sep='\t')

    def updateActiveSources(self):
        """This method updates the source combobox depending on the sources that are within the QTreeWidget within
        the GraphSettingsWindow object"""

        active_sources = self.settingsWindow.getActiveSources()  # get the list of source names within the QTreeWidget

        # get the list of current sources that are listed in the QCombobox
        current_sources = [self.source.itemText(i) for i in range(self.source.count())]

        # add items that are in active_sources but not in current_sources

        add_items = []
        [add_items.append(item) for item in active_sources if item not in current_sources]

        for item in add_items:
            current_sources.append(item)
            self.source.addItem(item)

        # remove items that are in current_sources that are not in active_sources

        remove_items = []
        [remove_items.append(item) for item in current_sources if item not in active_sources]

        for item in remove_items:
            self.source.removeItem(self.source.findText(item))

    def changeSources(self):

        data_source = self.source.currentText()

        if not hasattr(self.mainWindow, 'current_set_filename'):
            return

        session_path, set_filename = os.path.split(self.mainWindow.current_set_filename)
        session = os.path.splitext(set_filename)[0]
        source_filename = os.path.join(session_path, '%s%s' % (session, data_source))

        if not os.path.exists(source_filename):
            self.source_filename = None
            return

        else:
            self.source_filename = source_filename
        pass

    def findEOIs(self):

        # find the IDs of any existing EOIs
        iterator = QtGui.QTreeWidgetItemIterator(self.EOI)

        auto_IDs = []
        while iterator.value():
            item = iterator.value()
            auto_IDs.append(item.data(0, 0))
            iterator += 1

        self.EOI.clear()
        [self.IDs.pop(self.IDs.index(ID)) for ID in auto_IDs]  # remove the id from the list of IDs

        if 'Hilbert' in self.eoi_method.currentText():
            # EOIs = HilbertDetection(self)
            # dialog_self = QtGui.QWidget()
            # dialog = HilbertParametersWindow.HilbertDialog(dialog_self, self.mainWindow, self)
            # make sure to have the windows have a self. in front of them otherwise they will run and close
            self.hilbert_window = HilbertParametersWindow(self.mainWindow, self)

    def changeEventText(self, source):
        """This method will move the plot to the current selection"""
        if 'score' in source:
            # get the selected item

            for key, value in self.score_headers.items():
                if 'Start' in key:
                    start_value = value
                elif 'Stop' in key:
                    stop_value = value
            # root = self.scores.invisibleRootItem()
            try:
                item = self.scores.selectedItems()[0]
            except IndexError:
                return

            stop_time = float(item.data(stop_value, 0))
            start_time = float(item.data(start_value, 0))

        elif 'EOI' in source:

            for key, value in self.EOI_headers.items():
                if 'Start' in key:
                    start_value = value
                elif 'Stop' in key:
                    stop_value = value

            # get the selected item
            # root = self.EOI.invisibleRootItem()
            try:
                item = self.EOI.selectedItems()[0]
            except IndexError:
                # the item was probably deleted
                return

            stop_time = float(item.data(stop_value, 0))
            start_time = float(item.data(start_value, 0))

        self.customSignals.set_lr_signal.emit(str(start_time), str(stop_time))  # plots the lr at this time point

        time_value = np.round((stop_time + start_time) / 2 - self.mainWindow.windowsize / 2)

        # center the screen around the average of the stop_time and start_time
        # self.mainWindow.scrollbar.setValue(time_value / 1000 * self.mainWindow.SourceFs)

        self.mainWindow.current_time_object.setText(str(time_value))
        # self.mainWindow.setCurrentTime()

        # plot the start time

        self.mainWindow.start_time_object.setText(str(start_time))
        self.mainWindow.stop_time_object.setText(str(stop_time))

    def addEOI(self):
        '''This method will add the EOI values to the score list'''

        # get the detection method
        # method = self.eoi_method.currentText()

        if self.scorer.text() == '':
            self.mainWindow.choice = ''
            self.mainWindow.ErrorDialogue.myGUI_signal.emit("NoScorer")

            while self.mainWindow.choice == '':
                time.sleep(0.1)
            return

        # root = self.scores.invisibleRootItem()
        for item in self.EOI.selectedItems():

            # new_item = QtGui.QTreeWidgetItem()
            new_item = TreeWidgetItem()

            for score_key, score_value in self.score_headers.items():
                for eoi_key, eoi_value in self.EOI_headers.items():
                    if 'Score:' in score_key:
                        new_item.setText(score_value, self.EOI_score.currentText())
                        break

                    elif 'Scorer' in score_key:
                        new_item.setText(score_value, self.scorer.text())

                    elif eoi_key == score_key:
                        new_item.setText(score_value, item.data(eoi_value, 0))
                        break

            for item_children in range(self.EOI.topLevelItemCount()):
                query_item = self.EOI.topLevelItem(item_children)
                if item == query_item:
                    self.EOI.takeTopLevelItem(item_children)
                    break

            self.scores.addTopLevelItem(new_item)

            new_detected_events = str(int(self.events_detected.text()) - 1)
            self.events_detected.setText(new_detected_events)

    def deleteEOI(self):
        root = self.EOI.invisibleRootItem()
        item = self.EOI.selectedItems()[0]
        for item_count in range(self.EOI.topLevelItemCount()):
            query_item = self.EOI.topLevelItem(item_count)
            if query_item == item:
                # item_count += 1
                break

        for key, id_column in self.EOI_headers.items():
            if 'ID' in key:
                break
        ID = item.data(id_column, 0)
        self.IDs.pop(self.IDs.index(ID))
        (item.parent() or root).removeChild(item)

        # select the next item
        selected_item = self.EOI.topLevelItem(item_count).setSelected(True)

        # update the events detected
        new_detected_events = str(int(self.events_detected.text()) - 1)
        self.events_detected.setText(new_detected_events)

    def get_automatic_detection_filename(self):

        set_basename = os.path.basename(os.path.splitext(self.mainWindow.current_set_filename)[0])
        save_directory = os.path.dirname(self.score_filename.text())

        self.id_abbreviations[self.eoi_method.currentText().lower()]
        detection_method = self.eoi_method.currentText()

        save_filename = os.path.join(save_directory, '%s_%s.txt' % (set_basename, detection_method))

        return save_filename

    def loadAutomaticEOIs(self):

        # self.settings_fname = ''
        # save_filename = self.get_automatic_detection_filename()

        save_filename = self.eoi_filename.text()

        if 'Please add a source!' in save_filename:
            return

        save_filename, save_string_ext = QtGui.QFileDialog.getOpenFileName(self, 'Load EOI\'s',
                                                 save_filename,
                                                 'Text Files (*.txt)')
        if save_filename == '':
            return

        self.eoi_filename.setText(save_filename)

        if os.path.exists(save_filename):
            # do you want to overwrite this file?
            pass

        if os.path.exists(save_filename):
            df = pd.read_csv(save_filename, delimiter='\t')
        else:
            return

        # add the scores

        N = len(df)

        # find the IDs of any existing EOIs
        iterator = QtGui.QTreeWidgetItemIterator(self.EOI)

        auto_IDs = []
        while iterator.value():
            item = iterator.value()
            auto_IDs.append(item.data(0, 0))
            iterator += 1

        self.EOI.clear()
        [self.IDs.pop(self.IDs.index(ID)) for ID in auto_IDs]  # remove the id from the list of IDs

        ids_exist = any('ID' in column for column in df.columns)

        settings_filename_exist = any('Settings File' in column for column in df.columns)

        for key, value in self.EOI_headers.items():
            if 'ID' in key:
                id_value = value
            elif 'Settings File' in key:
                settings_value = value
            elif 'Start Time' in key:
                start_value = value

        for eoi_index in range(N):
            # item = QtGui.QTreeWidgetItem()
            item = TreeWidgetItem()

            if not ids_exist:
                ID = self.createID('Unknown')
                self.IDs.append(ID)
                item.setText(id_value, ID)

            if not settings_filename_exist:
                item.setText(settings_value, 'Unknown')

            for column in df.columns:

                if 'Unnamed' in column:
                    continue

                for key, value in self.EOI_headers.items():

                    if key == column:
                        if 'ID' in key:
                            ID = df[column][eoi_index]
                            self.IDs.append(ID)
                            item.setText(value, ID)

                        else:
                            item.setText(value, str(df[column][eoi_index]))

                    # these next statements are for the older files
                    elif 'Score' in column and 'Score:' in key:
                        item.setText(value, str(df[column][eoi_index]))

                    elif 'Start' in column and 'Start' in key:
                        item.setText(value, str(df[column][eoi_index]))

                    elif 'Stop' in column and 'Stop' in key:
                        item.setText(value, str(df[column][eoi_index]))


            self.EOI.addTopLevelItem(item)

        self.EOI.sortItems(start_value, QtCore.Qt.AscendingOrder)

        self.events_detected.setText(str(len(df)))

    def setEOIfilename(self):

        if not hasattr(self.mainWindow, 'current_set_filename'):
            return

        set_directory = os.path.dirname(self.mainWindow.current_set_filename)
        set_basename = os.path.basename(os.path.splitext(self.mainWindow.current_set_filename)[0])
        method = self.eoi_method.currentText()
        method = self.id_abbreviations[method.lower()]
        filename = os.path.join(set_directory, 'HFOScores',
                                set_basename,
                                '%s_%s.txt' % (set_basename, method))

        self.eoi_filename.setText(filename)

    def saveAutomaticEOIs(self):

        save_filename = self.eoi_filename.text()

        if 'Please add a source!' in save_filename:
            return

        save_filename, save_extension = QtGui.QFileDialog.getSaveFileName(self, 'Save EOI\'s',
                                                 save_filename,
                                                 'Text Files (*.txt)')

        if save_filename == '':
            return

        self.eoi_filename.setText(save_filename)

        # iterate through each item
        start_times = []
        stop_times = []
        ids = []

        # get the column values for each of the parameters
        for key, value in self.EOI_headers.items():
            if 'ID' in key:
                id_value = value
            elif 'Start' in key:
                start_value = value
            elif 'Stop' in key:
                stop_value = value

        for item_count in range(self.EOI.topLevelItemCount()):
            item = self.EOI.topLevelItem(item_count)

            ids.append(item.data(id_value, 0))
            start_times.append(item.data(start_value, 0))
            stop_times.append(item.data(stop_value, 0))

        data_dict = {}
        for key, value in self.score_headers.items():
            if 'ID' in key:
                data_dict[key] = ids

            elif 'Start' in key:
                data_dict[key] = pd.Series(start_times)

            elif 'Stop' in key:
                data_dict[key] = pd.Series(stop_times)

        df = pd.DataFrame(data_dict)

        # get filename

        # make the directory name if it does not exists already
        if not os.path.exists(os.path.dirname(save_filename)):
            os.makedirs(os.path.dirname(save_filename))

        df.to_csv(save_filename, sep='\t')


def HilbertDetection(self):
    # self is the scoreWindow

    if not hasattr(self, 'source_filename'):
        return

    if not os.path.exists(self.source_filename):
        return

    # get the raw data
    raw_data, Fs = self.settingsWindow.loaded_sources[self.source_filename]

    # band pass

    if self.max_freq != Fs/2 and self.min_freq != 0:
        filtered_data = filt.iirfilt(bandtype='band', data=raw_data, Fs=Fs,
                                                    Wp=self.min_freq, Ws=self.max_freq,
                                                    order=3, automatic=0, Rp=3, As=60, filttype='butter',
                                                    showresponse=0)
    elif self.max_freq == Fs/2:
        filtered_data = filt.iirfilt(bandtype='high', data=raw_data, Fs=Fs,
                                               Wp=self.min_freq, Ws=[],
                                               order=3, automatic=0, Rp=3, As=60, filttype='butter',
                                               showresponse=0)
    elif self.min_freq == 0:
        filtered_data = filt.iirfilt(bandtype='low', data=raw_data, Fs=Fs,
                                               Wp=self.max_freq, Ws=[],
                                               order=3, automatic=0, Rp=3, As=60, filttype='butter',
                                               showresponse=0)

    filtered_data -= np.mean(filtered_data)  # removing DC offset
    t = (1000 / Fs) * np.arange(len(filtered_data))

    # calculate the hilbert transformation of the filtered signal
    analytic_signal = hilbert(filtered_data)  # time consuming
    hilbert_envelope = np.abs(analytic_signal)

    # rectifies the signal
    rectified_signal = np.abs(filtered_data)  # this rectifies the signal

    # calculate the standard deviation of 5 minutes of envelope data

    # five_min_window_length = int(Fs * (5 * 60))
    epoch_window = int(self.epoch*Fs)

    i = 0

    EOIs = []
    latest_stop = - 0.1  # making it a small negative number to begin
    # boundary_fraction = 0.3

    # epoch length
    epochs = 0
    while i <= len(hilbert_envelope):
        epochs += 1
        i += epoch_window + 1

    i = 0
    while i <= len(hilbert_envelope):

        # iterates through each of the x minute epochs (5 minutes usually)
        # window_EOIs = []

        # gets the time of the window
        window_t = t[i:i+epoch_window+1]

        print('Analyzing times up to %f sec (%f percent of the data)' % (window_t[-1] / 1000, 100 * window_t[-1] / t[-1]))

        # eoi_rectified = rectified_signal[i:i + epoch_window + 1]  # rectified signal of epoch

        # gets the window data
        window_data = hilbert_envelope[i:i+epoch_window+1]

        # set the threshold at the mean of the envelope + 3 SD
        window_mean = np.mean(window_data)  # mean of the epcoh
        window_std = np.std(window_data)  # standard deviation of the epoch
        threshold = window_mean + self.sd_num*window_std  # threshold of the epoch

        # scan for signal events of high amplitude and sufficient duration
        eoi_signal = np.where(window_data >= threshold)[0]

        # finds the consecutive indices representing periods where the signal was continuously above threshold
        eoi_indices = find_consec(eoi_signal)
        ########## where for loop used to be ##############

        eoi_indices = [np.asarray(eoi) for eoi in eoi_indices]

        window_EOIs = np.zeros((len(eoi_indices), 2))  # pre-allocating space for the window_eois

        rejected_eois = []

        peri_boundary_time = 200 / 1000  # sec
        peri_boundary_samples = int(peri_boundary_time * Fs)

        # getting the data before the first point above threshold of each event to find the start time
        eoi_find_start_indices = np.asarray([np.arange(eoi[0] - peri_boundary_samples, eoi[0]) for eoi in eoi_indices])
        eoi_find_start_indices[
            eoi_find_start_indices < 0] = 0  # any values that are below the 0'th index are just placed at 0

        eoi_find_start_time = window_t[eoi_find_start_indices]  # converting matrix of indices to matrix of time values

        # finding the indices (row, col) where the data values are below threshold
        row, col = np.where(window_data[eoi_find_start_indices] <= self.boundary_fraction * threshold)

        # since they are two arrays, we will separate the columns array into a matrix where each row belongs to each eoi

        #  starts by finding consecutive indices where the row values are the same
        row_consec = np.asarray(
            find_same_consec(row))  # matrix where each row contains the indices of the each eoi within the col array

        # column[i] belongs to row[i] thus once you find the consecutive rows,
        # their respective columns have the same indices
        eoi_starts = [col[consec_value] for consec_value in
                      row_consec]  # contains the column index where the EOI reaches below the threshold

        valid_rows = np.unique(row)

        # for each row (one EOI per row) find the start time
        # the start of the EOIs are the closest to the threshold (thus should be the maximum value)
        eoi_starts = [eoi_find_start_time[row_index, np.amax(eoi_starts[np.where(valid_rows == row_index)[0][0]])]
                      for row_index in valid_rows]

        # set the 1st column of window_EOIs as the start values
        window_EOIs[valid_rows, 0] = eoi_starts

        # find rows that were not included
        rejected_eois.extend(np.setdiff1d(np.arange(len(eoi_indices)), np.unique(row)))

        eoi_find_start_indices = None
        eoi_find_start_time = None
        eoi_starts = None

        #  now finding the stop times  #

        # getting the data after the end of each event to find the end time
        eoi_find_stop_indices = np.asarray(
            [np.arange(eoi[-1] + 1, eoi[-1] + peri_boundary_samples + 1) for eoi in eoi_indices])

        # any values that are above the max index, are placed at the max index
        eoi_find_stop_indices[eoi_find_stop_indices > len(window_t) -1] = len(window_t) - 1

        eoi_find_stop_time = window_t[eoi_find_stop_indices]  # converting matrix of indices to matrix of time values

        # finding the indices (row, col) where the data values are below threshold
        row, col = np.where(window_data[eoi_find_stop_indices] <= self.boundary_fraction * threshold)

        # since they are two arrays, we will separate the columns array into a matrix where each row belongs to each eoi

        #  starts by finding consecutive indices where the row values are the same
        row_consec = np.asarray(
            find_same_consec(row))  # matrix where each row contains the indices of the each eoi within the col array

        eoi_stops = [col[consec_value] for consec_value in
                     row_consec]  # contains the column index where the EOI reaches below the threshold

        valid_rows = np.unique(row)

        eoi_stops = [eoi_find_stop_time[row_index, np.amin(eoi_stops[np.where(valid_rows == row_index)[0][0]])]
                     for row_index in valid_rows]

        window_EOIs[np.unique(row), 1] = eoi_stops

        rejected_eois.extend(np.setdiff1d(np.arange(len(eoi_indices)), np.unique(row)))

        eoi_find_stop_indices = None
        eoi_find_stop_time = None
        eoi_stops = None
        row = None
        col = None

        if rejected_eois != []:
            window_EOIs = np.delete(window_EOIs, rejected_eois, axis=0)  # removing rejected EOIs

        # remove overlapping EOIs

        if len(window_EOIs) == 0:
            i += epoch_window + 1
            continue

        latest_time = window_EOIs[0, -1]
        latest_index = 0
        rejected_eois = []

        # print(window_EOIs.shape)

        # merging EOIs that overlap
        for eoi_index, eoi in enumerate(window_EOIs):

            if eoi_index != 0:
                within_previous_bool = (eoi <= latest_time)
                if sum(within_previous_bool) == 2:
                    # this next eoi is within the previous one
                    rejected_eois.append(eoi_index)

                elif sum(within_previous_bool) == 1:
                    # then the start is within the previous eoi, but there is a new end

                    # the ending of the previous needs to be extended
                    window_EOIs[latest_index, 1] = eoi[-1]  # modify the ending of the latest_index
                    rejected_eois.append(eoi_index)
                    latest_time = eoi[-1]

                elif sum(within_previous_bool) == 0:
                    # this is an acceptable eoi
                    latest_time = eoi[-1]
                    latest_index = eoi_index

        if rejected_eois != []:
            window_EOIs = np.delete(window_EOIs, rejected_eois, axis=0)  # removing rejected EOIs

        if len(window_EOIs) == 0:
            i += epoch_window + 1
            continue
        # merging EOIs within 10ms of each other

        latest_time = window_EOIs[0, -1]
        latest_index = 0
        rejected_eois = []

        for eoi_index, eoi in enumerate(window_EOIs):

            if eoi_index != 0:

                if eoi[0] - latest_time < 10:
                    # merge EOI's that are less than 10 ms between each other
                    latest_time = eoi[-1]
                    window_EOIs[latest_index, -1] = latest_time
                    rejected_eois.append(eoi_index)
                else:
                    # this is an acceptable eoi
                    latest_time = eoi[-1]
                    latest_index = eoi_index

        if rejected_eois != []:
            window_EOIs = np.delete(window_EOIs, rejected_eois, axis=0)  # removing rejected EOIs

        if len(window_EOIs) == 0:
            i += epoch_window + 1
            continue
        # removing EOIs less than X ms

        rejected_eois = np.where(np.diff(window_EOIs) < self.min_duration)[0]
        if len(rejected_eois > 0):
            window_EOIs = np.delete(window_EOIs, rejected_eois, axis=0)  # removing rejected EOIs

        # end of where for loop used to be  #

        i += epoch_window + 1

        if window_EOIs == []:
            # then there were no EOIs found
            continue

        if window_EOIs.shape[0] == 0:
            continue

        rejected_sd = ()
        if self.required_peak_sd is None:
            required_peak_threshold = None
        else:
            required_peak_threshold = window_mean + self.required_peak_sd * window_std

        if len(EOIs) != 0:

            if window_EOIs[0, 0] - EOIs[-1, 1] < 10:
                # merge EOI's that are less than 10 ms between each other
                EOIs[-1, 1] = window_EOIs[0, 0]
                window_EOIs = window_EOIs[1:, :]

                # check if the latest event has the desired peaks at the desired threshold of the rectified signal
                # eoi_data = eoi_rectified[int(Fs * EOIs[-1, 0] / 1000):int(Fs * EOIs[-1, 1] / 1000) + 1]
                eoi_data = rectified_signal[int(Fs * EOIs[-1, 0] / 1000):int(Fs * EOIs[-1, 1] / 1000) + 1]

                peak_indices = detect_peaks(eoi_data, threshold=0)
                if not len(np.where(eoi_data[peak_indices] >= window_mean + 2 * window_std)[0]) >= 6:
                    EOIs = EOIs[:-1, :]

            window_EOIs = RejectEOIs(window_EOIs, rectified_signal, Fs, required_peak_threshold,
                                     self.required_peak_number)

            EOIs = np.vstack((EOIs, window_EOIs))
        else:

            EOIs = RejectEOIs(window_EOIs, rectified_signal, Fs, required_peak_threshold,
                              self.required_peak_number)

    if EOIs == []:
        # then there were no EOIs found
        print('No EOIs were found!')
        return

    self.events_detected.setText(str(len(EOIs)))

    for key, value in self.EOI_headers.items():
        if 'ID' in key:
            ID_value = value
        elif 'Start' in key:
            start_value = value
        elif 'Stop' in key:
            stop_value = value
        elif 'Settings' in key:
            settings_value = value

    for EOI in EOIs:
        # EOI_item = QtGui.QTreeWidgetItem()
        EOI_item = TreeWidgetItem()

        new_id = self.createID(self.eoi_method.currentText())
        self.IDs.append(new_id)
        EOI_item.setText(ID_value, new_id)
        EOI_item.setText(start_value, str(EOI[0]))
        EOI_item.setText(stop_value, str(EOI[1]))
        EOI_item.setText(settings_value, self.settings_fname)
        # there is a QTimer error, must add these from the main thread
        self.AddItemSignal.childAdded.emit(EOI_item)
        # self.EOI.addTopLevelItem(EOI_item)

    # self.saveAutomaticEOIs()


def find_same_consec(data):
    if len(data) == 1:
        return [0]

    diff_data = np.diff(data)

    consec_switch = np.where(diff_data != 0)[0]

    if len(consec_switch) == 0:
        # then it never switched
        return [np.arange(len(data))]

    consecutive_values = []

    if consec_switch[0] > 0:
        consecutive_values.append(np.arange(consec_switch[0] + 1))
    else:
        consecutive_values.append([0])
        if np.sum(np.in1d(consec_switch, [0])) == 0:
            consecutive_values.append(np.arange(1, consec_switch[1] + 1))

    for i in range(1, len(consec_switch)):
        consecutive_values.append(np.arange(consec_switch[i - 1] + 1, consec_switch[i] + 1))

    if consec_switch[-1] != len(data) - 1:
        consecutive_values.append(np.arange(consec_switch[-1] + 1, len(data)))

    return consecutive_values


def RejectEOIs(EOIs, rectified_signal, Fs, threshold, required_peaks):
    # reject events that don't have the required_peaks above the designated threshold, if there is no threshold and
    # you just want an N number of peaks, then leave the threshold as None (or blank in the GUI)
    rejected_eois = []

    for k in range(EOIs.shape[0]):

        eoi_data = rectified_signal[int(Fs * EOIs[k, 0] / 1000):int(Fs * EOIs[k, 1] / 1000) + 1]

        peak_indices = detect_peaks(eoi_data, threshold=0)

        if threshold is not None:

            if not len(np.where(eoi_data[peak_indices] >= threshold)[0]) >= required_peaks:
                rejected_eois.append(k)

        else:

            if not len(peak_indices) >= required_peaks:
                rejected_eois.append(k)

    window_EOIs = np.delete(EOIs, rejected_eois, axis=0)  # removing rejected EOIs

    return window_EOIs


def findStop(stop_indices):
    # checks which indices are consecutive from the first index given and finds that largest consecutive value to be
    # the stop index

    stop_index = stop_indices[0]

    if len(stop_indices) == 1:
        return stop_index

    for i in range(1, len(stop_indices) + 1):
        if stop_indices[i] == stop_index + 1:
            stop_index = stop_indices[i]
        else:
            break
    return stop_index


def findStart(start_indices):
    # checks which indices are consecutive from the last index given and finds that smallest consecutive value to be
    # the start index

    start_index = start_indices[-1]

    if len(start_indices) == 1:
        return start_index

    for i in range(len(start_indices)-2, -1, -1):
        if start_indices[i] == start_index - 1:
            start_index = start_indices[i]
        else:
            break
    return start_index


class HilbertParametersWindow(QtGui.QWidget):

    def __init__(self, main, score):
        super(HilbertParametersWindow, self).__init__()


        self.mainWindow = main
        self.scoreWindow = score

        # background(self)
        # width = self.deskW / 6
        # height = self.deskH / 1.5

        self.setWindowTitle(
            os.path.splitext(os.path.basename(__file__))[0] + " - Hilbert Parameters Window")  # sets the title of the window

        main_location = main.frameGeometry().getCoords()

        # self.setGeometry(main_location[2], main_location[1] + 30, width, height)

        self.HilbertParameters = ['Epoch(s):', '', 'Threshold(SD):',  '', 'Minimum Time(ms):', '',
                             'Min Frequency(Hz):', '', 'Max Frequency(Hz):', '', 'Required Peaks:', '',
                                  'Required Peak Threshold(SD):', '', 'Boundary Threshold(Percent)', '', '', '']

        self.hilbert_fields = {}
        self.Hilbert_field_positions = {}

        positions = [(i, j) for i in range(3) for j in range(6)]
        hilbert_parameter_layout = QtGui.QGridLayout()

        for (i, j), parameter in zip(positions, self.HilbertParameters):

            if parameter == '':
                continue
            else:
                self.Hilbert_field_positions[parameter] = (i, j)

                self.hilbert_fields[i, j] = QtGui.QLabel(parameter)
                self.hilbert_fields[i, j].setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

                self.hilbert_fields[i, j + 1] = QtGui.QLineEdit()
                self.hilbert_fields[i, j + 1].setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

                if 'Epoch' in parameter:
                    ParameterText = str(5*60)  # 5 minute epochs
                    self.hilbert_fields[i, j + 1].setToolTip(
                        'The data is broken up into epochs of this time period, there is a different threshold per epoch.')
                elif 'Threshold' in parameter and not any(x in parameter for x in ['Required', 'Boundary']):
                    ParameterText = '3'  # mean + 3 SD's
                    self.hilbert_fields[i, j + 1].setToolTip(
                        'The threshold is set to the mean of the epoch + X standard deviations of that epoch')
                elif 'Minimum' in parameter:
                    ParameterText = '10'  # minimum time of 6 ms'
                    self.hilbert_fields[i, j + 1].setToolTip(
                        'The minimum duration that an EOI must have in order to not be discarded')
                elif 'Min Freq' in parameter:
                    ParameterText = '80'  # minimum frequency of 100 Hz
                    self.hilbert_fields[i, j + 1].setToolTip(
                        'The minimum frequency of the filtered signal that then undergoes the Hilbert transform to find the EOIs.')
                elif 'Max Freq' in parameter:
                    ParameterText = '500'  # minimum frequency of 100 Hz
                    self.hilbert_fields[i, j + 1].setToolTip(
                        'The maximum frequency of the filtered signal that then undergoes the Hilbert transform to find the EOIs.')
                elif 'Required Peaks' in parameter:
                    ParameterText = '6'
                    self.hilbert_fields[i, j + 1].setToolTip(
                        'The required peaks (above the required peak threshold) of the recitfied signal that the EOI must have to not get discarded.')
                elif 'Required Peak Threshold' in parameter:
                    ParameterText = '2'
                    self.hilbert_fields[i, j + 1].setToolTip(
                        'The threshold for the the required peaks (mean + X standard deviations).')

                elif 'Boundary Threshold(Percent)' in parameter:
                    ParameterText = '30'
                    self.hilbert_fields[i, j + 1].setToolTip(
                        'The percentage of the threshold that will be used to determine the beginning and end of the EOI.')

                self.hilbert_fields[i, j + 1].setText(ParameterText)

                parameter_layout = QtGui.QHBoxLayout()
                parameter_layout.addWidget(self.hilbert_fields[i, j])
                parameter_layout.addWidget(self.hilbert_fields[i, j + 1])
                hilbert_parameter_layout.addLayout(parameter_layout, *(i, j))

        window_layout = QtGui.QVBoxLayout()

        Title = QtGui.QLabel("Automatic Detection - Hilbert")

        directions = QtGui.QLabel("Please ensure that the parameters listed below are correct. " +
                                  "if you are interested in Fast Ripples, I recommend bumping the " +
                                  "minimum frequency to 500Hz.")

        self.analyze_btn = QtGui.QPushButton("Analyze")
        self.analyze_btn.clicked.connect(self.analyze)

        self.cancel_btn = QtGui.QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.close_app)

        button_layout = QtGui.QHBoxLayout()

        for button in [self.analyze_btn, self.cancel_btn]:
            button_layout.addWidget(button)

        for order in [Title, directions, hilbert_parameter_layout, button_layout]:
            if 'Layout' in order.__str__():
                window_layout.addLayout(order)
                window_layout.addStretch(1)
            else:
                window_layout.addWidget(order, 0, QtCore.Qt.AlignCenter)
                window_layout.addStretch(1)

        self.setLayout(window_layout)

        center(self)

        self.show()

    def analyze(self):

        if not hasattr(self.scoreWindow, 'source_filename'):
            print('You have not chosen a source yet! Please add a source in the Graph Settings window!')
            return

        if not os.path.exists(self.scoreWindow.source_filename):
            return

        for parameter, (i, j) in self.Hilbert_field_positions.items():

            if parameter == '':
                continue

            if 'Min Freq' in parameter:
                min_freq_i, min_freq_j = (i, j)
            elif 'Max Freq' in parameter:
                max_freq_i, max_freq_j = (i, j)

        if '.egf' in self.scoreWindow.source_filename:
            # ParameterText = '500'  # maximum frequency of 400 Hz
            self.hilbert_fields[max_freq_i, max_freq_j + 1].setText('500')
        else:
            # ParameterText = '125'
            self.hilbert_fields[max_freq_i, max_freq_j + 1].setText('125')

        settings = {}
        for parameter, (i, j) in self.Hilbert_field_positions.items():

            if parameter == '':
                continue

            parameter_object = self.hilbert_fields[i, j+1]
            try:
                if 'Epoch' in parameter:
                    self.scoreWindow.epoch = float(parameter_object.text())
                    settings[parameter] = self.scoreWindow.epoch
                elif 'Threshold' in parameter and not any(x in parameter for x in ['Required', 'Boundary']):
                    self.scoreWindow.sd_num = float(parameter_object.text())
                    settings[parameter] = self.scoreWindow.sd_num
                elif 'Minimum' in parameter:
                    self.scoreWindow.min_duration = float(parameter_object.text())
                    settings[parameter] = self.scoreWindow.min_duration
                elif 'Min Freq' in parameter:
                    self.scoreWindow.min_freq = float(parameter_object.text())
                    settings[parameter] = self.scoreWindow.min_freq
                elif 'Max Freq' in parameter:
                    self.scoreWindow.max_freq = float(parameter_object.text())
                    settings[parameter] = self.scoreWindow.max_freq
                elif 'Required Peaks' in parameter:
                    self.scoreWindow.required_peak_number = float(parameter_object.text())
                    settings[parameter] = self.scoreWindow.required_peak_number
                elif 'Required Peak Threshold' in parameter:
                    value = parameter_object.text()
                    if value == '':
                        self.scoreWindow.required_peak_sd = None
                        settings[parameter] = value
                    else:
                        self.scoreWindow.required_peak_sd = float(value)
                        settings[parameter] = self.scoreWindow.required_peak_sd
                elif 'Boundary Threshold(Percent)' in parameter:
                    self.scoreWindow.boundary_fraction = float(parameter_object.text())/100
                    settings[parameter] = self.scoreWindow.boundary_fraction
            except ValueError:

                self.mainWindow.choice = ''
                self.mainWindow.ErrorDialogue.myGUI_signal.emit("InvalidDetectionParam")

                while self.mainWindow.choice == '':
                    time.sleep(0.1)

                return

        # save the EOI parameters
        # find any settings fnames
        method_abbreviation = self.scoreWindow.id_abbreviations['hilbert']
        session_path, set_filename = os.path.split(self.mainWindow.current_set_filename)
        session = os.path.splitext(set_filename)[0]

        hfo_path = os.path.join(session_path, 'HFOScores', session)

        if not os.path.exists(hfo_path):
            os.makedirs(hfo_path)

        settings_name = '%s_%s_settings' % (session, method_abbreviation)

        existing_settings_files = [os.path.join(hfo_path, file) for file in os.listdir(hfo_path) if settings_name in file]

        if len(existing_settings_files) >= 1:

            # check if any of these files has your settings
            match = False
            for file in existing_settings_files:
                with open(file, 'r+') as f:
                    file_settings = json.load(f)
                    if len(file_settings.items() & settings.items()) == len(file_settings.items()):
                        match = True
                        self.scoreWindow.settings_fname = file
                        break

            if not match:
                version = [int(os.path.splitext(file)[0].split('_')[-1]) for file in existing_settings_files if
                           os.path.splitext(file)[0].split('_')[-1] != 'settings']
                if len(version) == 0:
                    version = 1
                else:
                    version = np.amax(np.asarray(version)) + 1

                self.scoreWindow.settings_fname = os.path.join(hfo_path, '%s_%d.txt' % (settings_name, version))
                with open(self.scoreWindow.settings_fname, 'w') as f:
                    json.dump(settings, f)

        else:
            # no settings file for this session
            self.scoreWindow.settings_fname = os.path.join(hfo_path, '%s.txt' % (settings_name))
            with open(self.scoreWindow.settings_fname, 'w') as f:
                json.dump(settings, f)


        self.scoreWindow.hilbert_thread.start()
        self.scoreWindow.hilbert_thread_worker = Worker(HilbertDetection, self.scoreWindow)
        self.scoreWindow.hilbert_thread_worker.moveToThread(self.scoreWindow.hilbert_thread)
        self.scoreWindow.hilbert_thread_worker.start.emit("start")

        # HilbertDetection(self.scoreWindow)

        # self.hide()
        self.close()

    def close_app(self):

        self.close()


class SettingsViewer(QtGui.QWidget):

    def __init__(self, filename):
        super(SettingsViewer, self).__init__()
        background(self)
        width = self.deskW / 3
        height = self.deskH / 3
        self.setGeometry(0, 0, width, height)

        self.setWindowTitle("Settings Viewer Window")

        setting_fname_label = QtGui.QLabel("Settings Filename:")
        self.setting_filename = QtGui.QLineEdit()
        self.setting_filename.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
        self.setting_filename.setText(filename)

        settings_fname_layout = QtGui.QHBoxLayout()
        settings_fname_layout.addWidget(setting_fname_label)
        settings_fname_layout.addWidget(self.setting_filename)

        with open(filename, 'r+') as f:
            settings = json.load(f)

        parameter_label = QtGui.QLabel("Settings Parameters")
        # self.parameters = QtGui.QTextEdit()

        self.parameters = QtGui.QTreeWidget()

        self.parameters_headers = {'Parameter:': 0, "Value:": 1}
        for key, value in self.parameters_headers.items():
            self.parameters.headerItem().setText(value, key)

        for key, value in settings.items():
            # text = '%s\t%s' % (str(key), str(value))
            # self.parameters.append(text)
            # new_item = QtGui.QTreeWidgetItem()
            new_item = TreeWidgetItem()

            new_item.setText(self.parameters_headers['Parameter:'], str(key))
            new_item.setText(self.parameters_headers['Value:'], str(value))
            self.parameters.addTopLevelItem(new_item)

        parameters_layout = QtGui.QVBoxLayout()
        parameters_layout.addWidget(parameter_label)
        parameters_layout.addWidget(self.parameters)

        self.close_btn = QtGui.QPushButton("Close")
        self.close_btn.clicked.connect(self.close_app)

        settings_layout = QtGui.QVBoxLayout()

        for order in [settings_fname_layout, parameters_layout, self.close_btn]:
            if 'Layout' in order.__str__():
                settings_layout.addLayout(order)
                # layout_score.addStretch(1)
            else:
                # layout_score.addWidget(order, 0, QtCore.Qt.AlignCenter)
                settings_layout.addWidget(order)
                # layout_score.addStretch(1)

        self.setLayout(settings_layout)

        center(self)

        self.show()

    def close_app(self):

        self.close()
