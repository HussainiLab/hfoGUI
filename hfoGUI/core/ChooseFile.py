import os
import sys
from PyQt5 import QtWidgets, QtCore
from core.GUI_Utils import background, center


class ChooseFile(QtWidgets.QWidget):
    '''A popup widget that will occur when the user presses the Choose Set button
    on the main window'''
    def __init__(self, main, source):
        super(ChooseFile, self).__init__()
        background(self)
        width = int(self.deskW / 5)
        height = int(self.deskH / 5)
        self.setGeometry(0, 0, width, height)

        if 'lfp' in source.lower():

            if getattr(sys, 'frozen', False):

                self.setWindowTitle(
                    os.path.splitext(os.path.basename(sys.executable))[
                        0] + " - Choose LFP File")  # sets the title of the window

            else:

                self.setWindowTitle(
                    os.path.splitext(os.path.basename(__file__))[
                        0] + " - Choose LFP File")  # sets the title of the window

            # ---------------- defining instructions -----------------
            instr = QtWidgets.QLabel("Choose the LFP file that you want to analyze!")

            # -------------------------------------------------------
            for key, val in main.main_window_field_positions.items():
                if 'LFP Filename' in key:
                    i_file, j_file = val

            self.choosebtn = QtWidgets.QPushButton('Choose an LFP file!', self)
            self.choosebtn.setToolTip('Click to choose an LFP file!')
            self.cur_file_t = QtWidgets.QLabel('Current LFP Filepath:')  # the label saying Current Set file

            applybtn = QtWidgets.QPushButton('Apply', self)
            applybtn.clicked.connect(lambda: self.apply_file(main, 'LFP'))

        elif 'eeg' in source.lower():  # then Import EEG was pressed

            if getattr(sys, 'frozen', False):

                self.setWindowTitle(
                    os.path.splitext(os.path.basename(sys.executable))[
                        0] + " - Choose EEG File")  # sets the title of the window

            else:

                self.setWindowTitle(
                    os.path.splitext(os.path.basename(__file__))[
                        0] + " - Choose EEG File")  # sets the title of the window

            # ---------------- defining instructions -----------------
            instr = QtWidgets.QLabel("Choose the EEG file that you want to analyze!")

            # -------------------------------------------------------
            for key, val in main.main_window_field_positions.items():
                if 'EEG Filename' in key:
                    i_file, j_file = val

            self.choosebtn = QtWidgets.QPushButton('Choose an EEG file!', self)
            self.choosebtn.setToolTip('Click to choose an EEG file!')
            self.cur_file_t = QtWidgets.QLabel('Current EEG Filepath:')  # the label saying Current Set file

            applybtn = QtWidgets.QPushButton('Apply', self)
            applybtn.clicked.connect(lambda: self.apply_file(main, 'EEG'))

        elif 'set' in source.lower():

            if getattr(sys, 'frozen', False):

                self.setWindowTitle(
                    os.path.splitext(os.path.basename(sys.executable))[
                        0] + " - Choose Set File")  # sets the title of the window

            else:

                self.setWindowTitle(
                    os.path.splitext(os.path.basename(__file__))[
                        0] + " - Choose Set File")  # sets the title of the window

            # ---------------- defining instructions -----------------
            instr = QtWidgets.QLabel("Choose a Set file or a folder containing it!")

            # -------------------------------------------------------
            for key, val in main.main_window_field_positions.items():
                if 'Set Filename' in key:
                    i_file, j_file = val
            applybtn = QtWidgets.QPushButton('Apply', self)
            applybtn.clicked.connect(lambda: self.apply_file(main, 'Set'))

            self.choosebtn = QtWidgets.QPushButton('Choose a Set file!', self)
            self.choosebtn.setToolTip('Click to choose a Set file!')

            # New: allow choosing a folder that contains the .set
            self.choosefolderbtn = QtWidgets.QPushButton('Choose a Folder', self)
            self.choosefolderbtn.setToolTip('Click to choose a folder with a .set')
            self.choosefolderbtn.clicked.connect(lambda: new_Folder(self))

            self.cur_file_t = QtWidgets.QLabel('Current Set/File or Folder:')  # the label saying Current Set file

        # replace the main window with the new .set filename
        cur_file_name = main.main_window_fields[i_file, j_file + 1].text()

        # ----------------- buttons ----------------------------

        self.cur_file_e = QtWidgets.QLineEdit() # the label that states the current set filename
        self.cur_file_e.setText(cur_file_name)
        self.cur_file_e.setAlignment(QtCore.Qt.AlignHCenter)
        self.cur_file_name = cur_file_name

        self.backbtn = QtWidgets.QPushButton('Back',self)

        # ----------------- setting layout -----------------------

        layout_file = QtWidgets.QVBoxLayout()

        layout_h1 = QtWidgets.QHBoxLayout()
        layout_h1.addWidget(self.cur_file_t)
        layout_h1.addWidget(self.cur_file_e)

        btn_layout = QtWidgets.QHBoxLayout()
        btn_order = [self.choosebtn, self.choosefolderbtn, applybtn, self.backbtn]

        for butn in btn_order:
            btn_layout.addWidget(butn)

        layout_order = [instr, layout_h1, btn_layout]

        layout_file.addStretch(1)
        for order in layout_order:
            if 'Layout' in order.__str__():
                layout_file.addLayout(order)
                layout_file.addStretch(1)
            else:
                layout_file.addWidget(order, 0, QtCore.Qt.AlignCenter)
                layout_file.addStretch(1)

        self.setLayout(layout_file)

        center(self)

    def apply_file(self, main, source):

        self.cur_file_name = str(self.cur_file_e.text())
        main.file_fname = self.cur_file_name
        # find the position of the .set filename in the main window
        if 'lfp' in source.lower():
            for key, val in main.main_window_field_positions.items():
                if 'LFP Filename' in key:
                    i_file, j_file = val
        elif 'eeg' in source.lower():
            for key, val in main.main_window_field_positions.items():
                if 'EEG Filename' in key:
                    i_file, j_file = val
        else:
            for key, val in main.main_window_field_positions.items():
                if 'Set Filename' in key:
                    i_file, j_file = val

        # replace the main window with the new .set filename FIRST, then close
        main.main_window_fields[i_file, j_file + 1].setText(os.path.realpath(self.cur_file_name))
        self.backbtn.animateClick()


def new_File(self, main, source):
    '''A function that will be used from the Choose Set popup window that will
    produce a popup so the user can pick a filename for the .set file'''
    # prompt user to pick a .set file

    if 'set' in source.lower():
        cur_file_name, file_extension = QtWidgets.QFileDialog.getOpenFileName(self,
                                                                              "Select a Set file!",
                                                                              '',
                                                                              'Set Files (*.set)')
        # if no file chosen, skip
        if cur_file_name == '':
            return

        # replace the current .set field in the choose .set window with chosen filename
        self.cur_file_name = cur_file_name
        self.cur_file_e.setText(cur_file_name)
        return


def new_Folder(self):
    """Choose an existing folder; used for Set selection by folder."""
    folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Select a Folder Containing a .set", '')
    if folder == '':
        return
    self.cur_file_name = folder
    self.cur_file_e.setText(folder)
