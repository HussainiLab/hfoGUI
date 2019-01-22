# from pyqtgraph.Qt import QtGui, QtCore
# import matplotlib
# matplotlib.use('QT4Agg')
# from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
# from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import pyqtgraph as pg
# import matplotlib.pyplot as plt
# import pylab as plt
import numpy as np
from pyqtgraph.Qt import QtGui, QtCore
import sys
import os
import time
import functools

from core.GUI_Utils import background, Communicate, CustomViewBox, center, Worker
from core.GraphSettings import GraphSettingsWindows
from core.Score import ScoreWindow
from core.TFplots import TFPlotWindow

_author_ = "Geoffrey Barrett"  # defines myself as the author

Large_Font = ("Arial", 11)  # defines two fonts for different purposes (might not be used
Small_Font = ("Arial", 8)


class Window(QtGui.QWidget):  # defines the window class (main window)

    def __init__(self):  # initializes the main window
        super(Window, self).__init__()
        # self.setGeometry(50, 50, 500, 300)
        background(self)  # acquires some features from the background function we defined earlier

        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        # pg.setConfigOptions(antialias=True)
        # pg.setConfigOption('leftButtonPan', False)

        if getattr(sys, 'frozen', False):
            # frozen
            self.setWindowTitle(
                os.path.splitext(os.path.basename(sys.executable))[
                    0] + " - Main Window")  # sets the title of the window

        else:
            # unfrozen
            self.setWindowTitle(
                os.path.splitext(os.path.basename(__file__))[
                    0] + " - Main Window")  # sets the title of the window

        self.ErrorDialogue = Communicate()
        self.ErrorDialogue.myGUI_signal.connect(self.PopUpMessage)

        self.home()  # runs the home function

    def home(self):  # defines the home function (the main window)

        self.loaded_data = {}

        # ------ buttons + widgets -----------------------------

        self.graph_settings_btn = QtGui.QPushButton("Graph Settings", self)
        self.graph_settings_btn.setToolTip("Click if you want to add/remove waveforms, and edit the graph")

        self.score_btn = QtGui.QPushButton("Score", self)
        self.score_btn.setToolTip("Click if you want to score the EEG file")

        quit_btn = QtGui.QPushButton("Quit", self)
        quit_btn.clicked.connect(self.close_app)
        quit_btn.setShortcut("Ctrl+Q")
        quit_btn.setToolTip('Click to quit (or press Ctrl+Q)')

        self.TF_btn = QtGui.QPushButton("T-F Plots", self)
        self.TF_btn.setToolTip("Click to open a window showing the Time-Frequency plots (Stockwell)")

        btn_layout = QtGui.QHBoxLayout()

        button_order = [self.graph_settings_btn, self.score_btn, self.TF_btn, quit_btn]
        for button in button_order:
            btn_layout.addWidget(button)

        # Version information -------------------------------------------
        if getattr(sys, 'frozen', False):

            mod_date = time.ctime(os.path.getmtime(sys.executable))  # finds the modification date of the program

            vers_label = QtGui.QLabel(
                os.path.splitext(os.path.basename(sys.executable))[0] + " V1.1 - Last Updated: " + mod_date)

        else:

            mod_date = time.ctime(os.path.getmtime(__file__))  # finds the modification date of the program

            vers_label = QtGui.QLabel(
                os.path.splitext(os.path.basename(__file__))[0] + " V1.1 - Last Updated: " + mod_date)

        # ------------- grid layout ------------------------

        self.main_window_parameters = [
            'Import Set', 'Set Filename:', '', '', '', '', '',
        ]

        self.main_window_fields = {}
        self.main_window_field_positions = {}

        positions = [(i, j) for i in range(2) for j in range(7)]
        self.main_window_layout = QtGui.QGridLayout()

        for (i, j), parameter in zip(positions, self.main_window_parameters):

            if parameter == '':
                continue
            else:
                self.main_window_field_positions[parameter] = (i, j)
                if 'Import' in parameter:
                    self.main_window_fields[i, j] = QtGui.QPushButton(parameter, self)
                    self.main_window_layout.addWidget(self.main_window_fields[i, j], *(i,j))

                elif 'Set Filename' in parameter:
                    self.main_window_fields[i, j] = QtGui.QLabel(parameter)
                    self.main_window_fields[i, j].setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    #self.main_window_layout.addWidget(self.main_window_fields[i, j], *(i, j))
                    self.main_window_fields[i, j + 1] = QtGui.QLineEdit()
                    self.main_window_fields[i, j + 1].setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                    self.main_window_fields[i, j + 1].setText('Import a Set file!')
                    #self.main_window_fields[i, j + 1].textChanged.connect(ImportSet)

                    filename_layout = QtGui.QHBoxLayout()
                    filename_layout.addWidget(self.main_window_fields[i, j])
                    filename_layout.addWidget(self.main_window_fields[i, j + 1])
                    self.main_window_layout.addLayout(filename_layout, i, j, 1, 3)
                    #self.main_window_layout.addWidget(self.main_window_fields[i, j + 1], i, j + 1, 1, 5)

        # ------------------- setting the graph -----------------------
        self.GraphLoaded = False
        self.graphics_window = pg.GraphicsWindow()

        self.Graph_label = pg.LabelItem(justify='right')  # adds the Label that will be used for mouse interactions

        self.graphics_window.addItem(self.Graph_label)

        # adds the axis with custom viewbox to override the right click
        self.Graph_axis = self.graphics_window.addPlot(row=1, col=0, viewBox=CustomViewBox(self, self.graphics_window))
        self.Graph_axis.hideButtons()
        # self.Graph_axis

        # self.Graph_axis = self.graphics_window.addPlot(row=1, col=0)

        self.vb = self.Graph_axis.vb

        self.Graph_axis.setMouseEnabled(x=False, y=False)  # disables the mouse interactions

        self.Graph_axis.setLabel('bottom', "Time", units='ms')  # adds the x label

        self.GraphLayout = QtGui.QVBoxLayout()
        self.GraphLayout.addLayout(self.main_window_layout)

        self.GraphLayout.addWidget(self.graphics_window)

        self.scrollbar = QtGui.QScrollBar(QtCore.Qt.Horizontal)

        # self.scrollbar.actionTriggered.connect(self.ScrollGraph)
        self.scrollbar.actionTriggered.connect(functools.partial(self.changeCurrentGraph, 'scroll'))
        self.GraphLayout.addWidget(self.scrollbar)
        self.current_time = []

        # -------------- graph settigns -------------------------------

        self.graph_parameters = [
            'Window Size(ms):', '', 'Current Time(ms):', '', 'Start Time(ms):', '', 'Stop Time(ms):', '', 'Plot Spikes', ''
        ]
        self.graph_parameter_fields = {}
        self.graph_parameter_field_positions = {}

        positions = [(i, j) for i in range(1) for j in range(10)]
        self.graph_parameter_layout = QtGui.QGridLayout()

        for (i, j), parameter in zip(positions, self.graph_parameters):

            if parameter == '':
                continue
            else:
                self.graph_parameter_field_positions[parameter] = (i, j)

                if 'Plot' in parameter:
                    self.graph_parameter_fields[i, j+1] = QtGui.QCheckBox(parameter)
                    self.graph_parameter_layout.addWidget(self.graph_parameter_fields[i, j + 1], i, j + 1)

                else:

                    self.graph_parameter_fields[i, j] = QtGui.QLabel(parameter)
                    self.graph_parameter_layout.addWidget(self.graph_parameter_fields[i, j], *(i, j))
                    self.graph_parameter_fields[i, j + 1] = QtGui.QLineEdit()
                    self.graph_parameter_fields[i, j + 1].setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                    self.graph_parameter_layout.addWidget(self.graph_parameter_fields[i, j + 1], i, j+1)
                    if 'Window Size' in parameter:
                        self.i_windowsize, self.j_windowsize = (i, j)
                        self.graph_parameter_fields[i, j + 1].textChanged.connect(self.ChangeWindowSize)
                    elif 'Amplitude' in parameter:
                        pass
                        #self.graph_parameter_fields[i, j + 1].textChanged.connect(self.setCurrentTime)
                    elif 'Current Time' in parameter:
                        self.i_current_time, self.j_current_time = (i, j)
                        self.graph_parameter_fields[i, j + 1].textChanged.connect(functools.partial(self.changeCurrentGraph, 'text'))
                        pass
                        #self.graph_parameter_fields[i, j + 1].textChanged.connect(self.setCurrentTime)
                    elif 'Start Time' in parameter or 'Stop Time' in parameter:
                        self.graph_parameter_fields[i, j + 1].textChanged.connect(self.changeEventTimes)

        # ------------- layout ------------------------------

        layout = QtGui.QVBoxLayout()

        layout_order = [self.GraphLayout, self.graph_parameter_layout, btn_layout]

        for order in layout_order:
            if 'Layout' in order.__str__():
                layout.addLayout(order)
                layout.addStretch(1)
            else:
                layout.addWidget(order, 0, QtCore.Qt.AlignCenter)
                layout.addStretch(1)

        layout.addStretch(1)  # adds stretch to put the version info at the buttom
        layout.addWidget(vers_label)  # adds the date modification/version number

        self.setLayout(layout)

        center(self)

        self.show()

        self.set_parameters('Default')

    def create_lr(self):

        """This method will create the linear region item which will allow the user to select/score the events
        manually"""

        self.lr = pg.LinearRegionItem()  # adding a linear region selector
        self.lr.setZValue(-10)
        self.lr.hide()  # hiding, otherwise the whole screen will be selected
        self.Graph_axis.addItem(self.lr)

    def mouseMoved(self, evt):
        pos = evt[0]  ## using signal proxy turns original arguments into a tuple
        if self.Graph_axis.sceneBoundingRect().contains(pos):
            mousePoint = self.vb.mapSceneToView(pos)
            index = int(mousePoint.x())

            if index > 0:
                self.Graph_label.setText(
                    "<span style='font-size: 12pt'>Time=%0.1f ms, Total Duration: %0.1f sec" % (
                    mousePoint.x(), self.source_duration))
            self.mouse_vLine.setPos(mousePoint.x())
            # self.mouse_hLine.setPos(mousePoint.y())

    def drag(self, ev):
        # global vb, lr
        if (ev.button() == QtCore.Qt.LeftButton):
            self.lr.show()  # showing the linear region selector

            # defining the selected region
            self.lr.setRegion([self.vb.mapToView(ev.buttonDownPos()).x(), self.vb.mapToView(ev.pos()).x()])
            self.score_x1 = self.vb.mapToView(ev.buttonDownPos()).x()  # defining the start of the selected region
            self.score_x2 = self.vb.mapToView(ev.pos()).x()  # defining the end of the selected region
            ev.accept()
        else:
            pg.ViewBox.mouseDragEvent(self.vb, ev)

    def set_lr(self, value1, value2):
        value1 = np.float(value1)
        value2 = np.float(value2)
        self.score_x1 = value1
        self.score_x2 = value2
        self.lr.show()
        self.lr.setRegion([value1, value2])

    def close_app(self):

        # pop up window that asks if you really want to exit the app ------------------------------------------------

        choice = QtGui.QMessageBox.question(self, "Quitting ",
                                            "Do you really want to exit?",
                                            QtGui.QMessageBox.Yes | QtGui.QMessageBox.No)
        if choice == QtGui.QMessageBox.Yes:
            sys.exit()  # tells the app to quit
        else:
            pass

    def ChangeWindowSize(self):

        if self.GraphLoaded:
            self.get_parameters()
            self.scrollbar.setMinimum(0)
            self.scrollbar.setMaximum(self.SourceLength - (self.windowsize/1000 * self.SourceFs))
            self.scrollbar.setPageStep(self.windowsize/1000 * self.SourceFs / 3)
            self.scrollbar.setSingleStep(self.windowsize/1000 * self.SourceFs / 15)
            self.scrollbar.setValue((self.current_time/1000)*self.SourceFs)
            # self.Graph_axis.axis([self.current_time, self.current_time + self.windowsize, 0, self.graph_max])
            self.Graph_axis.setXRange(self.current_time, self.current_time + self.windowsize)
            self.Graph_axis.setYRange(0, self.graph_max)
            # self.GraphCanvas.draw()

    def ScrollGraph(self):
        '''This method makes the current time field match the scrollbar value'''
        if self.GraphLoaded:
            self.current_time_object.setText(str(self.scrollbar.value() * 1000 / self.SourceFs))

    def changeCurrentGraph(self, source):
        if not self.GraphLoaded:
            return

        if 'scroll' in source:
            self.ScrollGraph()

        elif 'text' in source:
            try:
                time = float(self.current_time_object.text())
                self.scrollbar.setValue(int(time / 1000 * self.SourceFs))
            except ValueError:
                return

    def setCurrentTime(self):

        while not self.GraphLoaded:
            time.sleep(0.1)
            self.previous_current_time = 0

        '''
        avgFps = 0
        avg_fps = []
        times = []
        '''

        while self.GraphLoaded:
            # now = pg.ptime.time()

            # time1 = pg.ptime.time()
            self.get_parameters()  # sets the current time
            self.get_scroll_values()
            # times.append(pg.ptime.time() - time1)

            try:
                if self.current_time < 0:
                    pass
                try:
                    if self.previous_current_time != self.current_time:
                        # self.Graph_axis.axis([self.current_time, self.current_time + self.windowsize, 0, self.graph_max])
                        self.Graph_axis.setXRange(self.current_time, self.current_time + self.windowsize, padding=0)
                        # self.Graph_axis.setYRange(self.current_time, self.current_time + self.windowsize, padding=0)

                        # self.GraphCanvas.draw()
                        self.previous_current_time = self.current_time
                        # time.sleep(0.001) # stops the figure from flashing white when the graph is re-drawn

                        '''
                        try:
                            fps = 1.0 / (now - self.last_update)
                            avgFps = avgFps * 0.8 + fps * 0.2
                            avg_fps.append(avgFps)
                            # print(avgFps)
                        except:
                            pass
                        self.last_update = now
                        '''

                except AttributeError:
                    pass
            except TypeError:
                pass

    def get_window_indices(self):
        self.get_parameters()  # sets the current time

        window_minimum = self.current_time
        window_maximum = self.current_time + self.windowsize

        #window_minimum_index = (window_minimum / 1000) * self.SourceFs
        #window_maximum_index = (window_maximum / 1000) * self.SourceFs

        #return int(window_minimum_index), int(window_maximum_index)

        return window_minimum, window_maximum

    def set_parameters(self, mode):
        if mode == 'Default':
            default_settings = {'Window Size': '500', 'Amplitude':'1000', 'Current Time':0, 'Plot Spikes':0}
            for parameter, position in self.graph_parameter_field_positions.items():
                for default_parameter, default_value in default_settings.items():
                    if default_parameter in parameter:
                        if 'LineEdit' in str(self.graph_parameter_fields[position[0], position[1]+1]):
                            self.graph_parameter_fields[position[0], position[1]+1].setText(str(default_value))
                        elif 'QCheckBox' in str(self.graph_parameter_fields[position[0], position[1] + 1]):
                            if default_value == 1:
                                # Check the CheckBox
                                self.graph_parameter_fields[position[0], position[1] + 1].toggle()
                            else:
                                pass
        else:
            for parameter, position in self.graph_parameter_field_positions.items():
                pass

    def set_current_filename(self):
        """This function will set the current filename"""
        for parameter, position in self.main_window_field_positions.items():
            if "EEG Filename" in parameter:
                self.cur_eeg_filename = self.main_window_fields[position[0], position[1] + 1].text()
            elif 'LFP Filename' in parameter:
                self.cur_lfp_filename = self.main_window_fields[position[0], position[1] + 1].text()
            elif 'Set Filename' in parameter:
                self.current_set_filename = self.main_window_fields[position[0], position[1] + 1].text()

    def get_scroll_values(self):
        try:
            self.current_time = float(self.graph_parameter_fields[self.i_current_time, self.j_current_time + 1].text())
        except ValueError:
            self.current_time = None

        try:
            self.windowsize = float(self.graph_parameter_fields[self.i_windowsize, self.j_windowsize + 1].text())
        except ValueError:
            self.windowsize = None

    def get_current_time(self):
        try:
            self.current_time = float(self.graph_parameter_fields[self.i_current_time, self.j_current_time + 1].text())
        except ValueError:
            self.current_time = None

    def get_window_size(self):
        try:
            self.windowsize = float(self.graph_parameter_fields[self.i_windowsize, self.j_windowsize + 1].text())
        except ValueError:
            self.windowsize = None

    def get_parameters(self):
        """This was one large function that would search through every widget for values and update the class attributes
        however, this is also used in updating the plots so I figured it could be slowing things down and refactored out
        some of the get/set portions
        """

        for parameter, position in self.graph_parameter_field_positions.items():
            if 'Window Size' in parameter:
                if self.graph_parameter_fields[position[0], position[1] + 1].text() == '':
                    continue
                try:
                    self.windowsize = float(self.graph_parameter_fields[position[0], position[1] + 1].text())
                except ValueError:
                    self.windowsize = None

            # elif 'Amp' in parameter:
            #     if self.graph_parameter_fields[position[0], position[1] + 1].text() == '':
            #         continue
            #     self.amplitude = float(self.graph_parameter_fields[position[0], position[1] + 1].text())
            elif 'Current Time' in parameter:
                if self.graph_parameter_fields[position[0], position[1] + 1].text() == '':
                    continue
                try:
                    self.current_time = float(self.graph_parameter_fields[position[0], position[1] + 1].text())
                except ValueError:
                    self.current_time = None

            elif 'Plot Spike' in parameter:
                self.plot_spikes = self.graph_parameter_fields[position[0], position[1] + 1].isChecked()
            elif 'Start Time' in parameter:
                try:
                    self.start_time = float(self.graph_parameter_fields[position[0], position[1] + 1].text())
                except ValueError:
                    self.start_time = None
            elif 'Stop Time' in parameter:
                try:
                    self.stop_time = float(self.graph_parameter_fields[position[0], position[1] + 1].text())
                except ValueError:
                    self.stop_time = None

    def PopUpMessage(self, error):

        if 'NoSetBits2uV' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: Bits2uV Error - No .Set File!",
                                                     "Bits2uV requires access to the .Set file for\n" +
                                                     "the appropriate parameters to convert from bits\n" +
                                                     "to micro-volts. The .Set file isn't in the directory,\n" +
                                                     "do you want hfoGUI to find the .Set file?",
                                                     QtGui.QMessageBox.Yes | QtGui.QMessageBox.Abort)

        elif 'NoAutoSet' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: .Set Search Error!",
                                                     "The appropriate .Set file could not be found after\n" +
                                                     "attempting to search for it through various directories,\n" +
                                                     "on this PC. Please place the .Set file in the same directory\n" +
                                                     "as the .EEG file!",
                                                     QtGui.QMessageBox.Ok)

        elif 'NoScorer' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: No Scorer!",
                                                     "Before scoring please type in the 'Scorer' Field who\n" +
                                                     "is scoring this file, then you can continue!\n",
                                                     QtGui.QMessageBox.Ok)

        elif 'ImportSetError' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: No Set Imported!",
                                                     "Import a '.set' file before continuing!\n",
                                                     QtGui.QMessageBox.Ok)

        elif 'InvalidSourceFname' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: Invalid Source filename!",
                                                     "The source filename you have chosen does not exist!\n" +
                                                     "please choose an existing filename!\n",
                                                     QtGui.QMessageBox.Ok)

        elif 'NegativeCutoff' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: Negative Cutoff Error!",
                                                     "Please choose positive cutoff values!\n",
                                                     QtGui.QMessageBox.Ok)

        elif 'InvalidCutoff' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: Invalid Cutoff!",
                                                     "The chosen cutoff is invalid!\n",
                                                     QtGui.QMessageBox.Ok)

        elif 'EGFNecessary' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: Cutoff Too High!",
                                                     "The EEG files are sampled at 250 Hz thus,\n" +
                                                     "the cutoff needs to be below 125 Hz!\n",
                                                     QtGui.QMessageBox.Ok)

        elif 'InvalidEGFCutoff' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: EGF Cutoff Too High!",
                                                     "The EGF files are sampled at 4800 Hz thus,\n" +
                                                     "the cutoff needs to be below 2400 Hz!\n",
                                                     QtGui.QMessageBox.Ok)

        elif 'ScoreFileExists' in error:

            filename = error[error.find(':')+1:]
            self.choice = QtGui.QMessageBox.question(self, "Error: Score Filename Exists!",
                                                     "The filename already exists, do you want to\n" +
                                                     "overwrite this score filename!\n\n" +
                                                     "Filename: %s\n" % filename,
                                                     QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel)

        elif 'MemoryError' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: Memory Error!",
                                                     "This action caused a memory error!",
                                                     QtGui.QMessageBox.Yes | QtGui.QMessageBox.Cancel)

        elif 'ScoreFileExistError' in error:

            filename = error[error.find(':') + 1:]
            self.choice = QtGui.QMessageBox.question(self, "Error: Score Filename Doesn't Exist!",
                                                     "The filename doesn't exist there we cannot load scores,\n" +
                                                     "please score a file before trying to load it!\n\n" +
                                                     "Filename: %s\n" % filename,
                                                     QtGui.QMessageBox.Ok | QtGui.QMessageBox.Cancel)
        elif 'InvalidDetectionParam' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: Invalid Automatic Detection Parameter!",
                                                     "One of designated parameters is invalid,\n" +
                                                     "please use the correct parameter format!\n",
                                                     QtGui.QMessageBox.Ok)

        elif 'ZeroCutoffError' in error:
            self.choice = QtGui.QMessageBox.question(self, "Error: Zero Cutoff Error",
                                                     "A filter cutoff value is set to zero, this is not allowed. If you want" +
                                                     "to include zero, use a lowpass filter.",
                                                     QtGui.QMessageBox.Ok)

    def changeEventTimes(self):
        '''This method will change the Start Time and Stop Time fields, as well as plot these locations as a vertical
        line'''
        if not hasattr(self, 'graph_max'):
            return

        self.get_parameters()  # sets the current time

        start_time = self.start_time
        stop_time = self.stop_time

        if start_time is None and stop_time is None:
            try:
                self.Graph_axis.removeItem(self.start_line)
            except:
                pass

            try:
                self.Graph_axis.removeItem(self.stop_line)
            except:
                pass


        if start_time is not None and stop_time is not None:
            if start_time >= stop_time:
                # re-arranges the order if the stop time is ever smaller than the start_time
                temp = np.array([start_time, stop_time])
                start_time = temp[1]
                stop_time = temp[0]
                temp = None

        if start_time is not None:

            try:
                # self.start_line.remove()
                self.Graph_axis.removeItem(self.start_line)
            except:
                pass

            '''
            self.start_line = self.Graph_axis.vlines(self.start_time, 0, self.graph_max, lw=2, 
                                                     color='r', linestyles='dashed')
            '''
            self.start_line = pg.InfiniteLine(pos=start_time, angle=90, pen=(255, 0, 0))

            self.Graph_axis.addItem(self.start_line)

        else:
            try:
                self.start_line.remove()
            except:
                pass

        if stop_time is not None:

            try:
                # self.stop_line.remove()
                self.Graph_axis.removeItem(self.stop_line)
            except:
                pass

            '''
            self.stop_line = self.Graph_axis.vlines(self.stop_time, 0,
                                                                          self.graph_max, lw=2,
                                                                          color='g', linestyles='dashed')
            '''
            self.stop_line = pg.InfiniteLine(pos=stop_time, angle=90,
                                              pen=(0, 255, 0))

            self.Graph_axis.addItem(self.stop_line)
        else:
            try:
                self.stop_line.remove()
            except:
                pass

        # self.GraphCanvas.draw()


class ChooseFile(QtGui.QWidget):
    '''A popup widget that will occur when the user presses the Choose Set button
    on the main window'''
    def __init__(self, main, source):
        super(ChooseFile, self).__init__()
        background(self)
        width = self.deskW / 5
        height = self.deskH / 5
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
            instr = QtGui.QLabel("Choose the LFP file that you want to analyze!")

            # -------------------------------------------------------
            for key, val in main.main_window_field_positions.items():
                if 'LFP Filename' in key:
                    i_file, j_file = val

            self.choosebtn = QtGui.QPushButton('Choose an LFP file!', self)
            self.choosebtn.setToolTip('Click to choose an LFP file!')
            self.cur_file_t = QtGui.QLabel('Current LFP Filepath:')  # the label saying Current Set file

            applybtn = QtGui.QPushButton('Apply', self)
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
            instr = QtGui.QLabel("Choose the EEG file that you want to analyze!")

            # -------------------------------------------------------
            for key, val in main.main_window_field_positions.items():
                if 'EEG Filename' in key:
                    i_file, j_file = val

            self.choosebtn = QtGui.QPushButton('Choose an EEG file!', self)
            self.choosebtn.setToolTip('Click to choose an EEG file!')
            self.cur_file_t = QtGui.QLabel('Current EEG Filepath:')  # the label saying Current Set file

            applybtn = QtGui.QPushButton('Apply', self)
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
            instr = QtGui.QLabel("Choose the Set file that you want to analyze!")

            # -------------------------------------------------------
            for key, val in main.main_window_field_positions.items():
                if 'Set Filename' in key:
                    i_file, j_file = val
            applybtn = QtGui.QPushButton('Apply', self)
            applybtn.clicked.connect(lambda: self.apply_file(main, 'Set'))

            self.choosebtn = QtGui.QPushButton('Choose a Set file!', self)
            self.choosebtn.setToolTip('Click to choose a Set file!')

            self.cur_file_t = QtGui.QLabel('Current Set Filepath:')  # the label saying Current Set file

        # replace the main window with the new .set filename
        cur_file_name = main.main_window_fields[i_file, j_file + 1].text()

        # ----------------- buttons ----------------------------

        self.cur_file_e = QtGui.QLineEdit() # the label that states the current set filename
        self.cur_file_e.setText(cur_file_name)
        self.cur_file_e.setAlignment(QtCore.Qt.AlignHCenter)
        self.cur_file_name = cur_file_name

        self.backbtn = QtGui.QPushButton('Back',self)


        # ----------------- setting layout -----------------------

        layout_file = QtGui.QVBoxLayout()

        layout_h1 = QtGui.QHBoxLayout()
        layout_h1.addWidget(self.cur_file_t)
        layout_h1.addWidget(self.cur_file_e)

        btn_layout = QtGui.QHBoxLayout()
        btn_order = [self.choosebtn, applybtn, self.backbtn]

        # btn_layout.addStretch(1)
        for butn in btn_order:
            btn_layout.addWidget(butn)
            # btn_layout.addStretch(1)

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
        # self.show()

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

        # replace the main window with the new .set filename
        self.backbtn.animateClick()
        main.main_window_fields[i_file, j_file + 1].setText(os.path.realpath(self.cur_file_name))


def new_File(self, main, source):
    '''A function that will be used from the Choose Set popup window that will
    produce a popup so the user can pick a filename for the .set file'''
    # prompt user to pick a .set file

    if 'set' in source.lower():
        cur_file_name = str(QtGui.QFileDialog.getOpenFileName(self, "Select a Set file!", '', 'Set Files (*.set)'))

    # if no file chosen, skip
    if cur_file_name == '':
        return

    # replace the current .set field in the choose .set window with chosen filename
    self.cur_file_name = cur_file_name
    self.cur_file_e.setText(cur_file_name)
    return

@QtCore.pyqtSlot()
def raise_w(new_window, old_window, source=''):
    """ raise the current window"""
    if 'ChooseFile' in str(new_window):

        if 'lfp' in source.lower():
            for key, val in old_window.main_window_field_positions.items():
                if 'LFP Filename' in key:
                    i, j = val
                    break
        elif 'eeg' in source.lower():
            for key, val in old_window.main_window_field_positions.items():
                if 'EEG Filename' in key:
                    i, j = val
                    break
        elif 'set' in source.lower():
            for key, val in old_window.main_window_field_positions.items():
                if 'Set Filename' in key:
                    i, j = val
                    break

        new_window.cur_file_e.setText(old_window.main_window_fields[i, j + 1].text())  # setting the current text field
        new_window.raise_()
        new_window.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        new_window.show()
        time.sleep(0.1)

    elif any(x in str(new_window) for x in ['Score','GraphSettings','TFPlot', 'PSDPlot']):
        new_window.raise_()
        #new_window.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        new_window.show()
        time.sleep(0.1)
    elif "Choose" in str(old_window):
        time.sleep(0.1)
        old_window.hide()
        return
    else:
        new_window.raise_()
        new_window.show()
        time.sleep(0.1)
        old_window.hide()

@QtCore.pyqtSlot()
def raise_detection_window(new_window, old_window):
    """ raise the current window"""
    if any(analysis in str(new_window) for analysis in ['Hilbert', ]):
        new_window.raise_()
        new_window.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
        new_window.show()
        time.sleep(0.1)
    else:
        new_window.raise_()
        new_window.show()
        time.sleep(0.1)
        old_window.hide()


def clear_all(main_window, graph_options_window, score_window, tf_plots_window):
    main_window.loaded_data = {}
    main_window.current_time = 0

    graph_options_window.loaded_sources = {}
    graph_options_window.cell_spike_time_array = []
    graph_options_window.cell_labels = []
    main_window.GraphLoaded = False

    main_window.Graph_axis.clear()
    # main_window.GraphCanvas.draw()

    # clear current scores
    score_window.scores.clear()
    score_window.EOI.clear()
    score_window.initialize_attributes()

    graph_options_window.graphs.clear()
    graph_options_window.FilterResponseAxis.clear()
    graph_options_window.FilterResponseCanvas.draw()
    graph_options_window.initialize_attributes()

    tf_plots_window.clearPlots()


def ImportSet(main_window, graph_options_window, score_window, tf_plots_window):
    """Updates the fields of the graph options window when the .set file changes"""
    if hasattr(main_window, 'scrollbar_thread'):
        # main_window.scrollbar_thread.quit()
        main_window.scrollbar_thread.terminate()

    main_window.set_current_filename()  # update the new filename

    # update the parameters from the Main Window
    main_window.get_parameters()

    # Loading the EEG

    desired_set_extgension = ['.set', '.egf']
    if main_window.current_set_filename == '' or all(desired_set_extgension[i] not in main_window.current_set_filename for i in
                                          range(len(desired_set_extgension))):
        return

    set_basename = os.path.basename(os.path.splitext(main_window.current_set_filename)[0])
    set_directory = os.path.dirname(main_window.current_set_filename)

    # finding EEG files and LFP files within the same directory
    try:
        directory_file_list = os.listdir(set_directory)
    except FileNotFoundError:
        return
    except PermissionError:
        return

    eeg_files = [file for file in directory_file_list if set_basename+'.eeg' in file or set_basename+'.egf' in file]
    lfp_files = []
    main_window.active_tetrodes = []
    #undesired_extensions = ['.ini', '.cut', '.clu', '.txt', '.ini']
    invalid_types = ['.clu', '.eeg', '.egf', '.set', '.cut', '.fmask', '.fet', '.klg', '.pos', '.SET', '.ini', '.txt']
    lfp_files = [file for file in directory_file_list
                if not any(x in file for x in invalid_types) and not os.path.isdir(os.path.join(set_directory, file))
                and any('%s.%d' % (set_basename, i) in file for i in range(1, 257))]

    pos_files = [file for file in directory_file_list if set_basename+'.pos' in file or set_basename+'.egf' in file]

    source_files = eeg_files + pos_files
    #desired_file_list = [file for file in directory_file_list and any(x not in file for x in undesired_extensions)]

    #[[lfp_files.append(file)for file in desired_file_list if set_basename+'.%d' % i in file]  for i in range(256)]

    [main_window.active_tetrodes.append(int((os.path.splitext(file)[1])[1:])) for file in lfp_files]
    for option, position in graph_options_window.graph_header_option_positions.items():
        if 'source' in option.lower():
            i, j = position # found the Source combobox in the Graph Settings Window
            break

    graph_combobox = graph_options_window.graph_header_option_fields[i, j + 1]
    graph_combobox.clear()

    graph_options_window.source_extensions = []

    # This will add the "sources' for the graph settings window
    for file in source_files:
        file_extension = os.path.splitext(file)[-1]
        if '.pos' not in file_extension:
            graph_combobox.addItem(file_extension)
        else:
            graph_combobox.addItem('Speed')

    # replace the score with a new proper score file
    score_filename = os.path.join(set_directory, 'HFOScores', set_basename, '%s_HFOScores.txt' % set_basename)
    score_window.score_filename.setText(score_filename)

    score_window.setEOIfilename()

    clear_all(main_window, graph_options_window, score_window, tf_plots_window)

    # proxy = pg.SignalProxy(self.mainWindow.Graph_axis.scene().sigMouseMoved, rateLimit=60, slot=self.mainWindow.mouseMoved)

    main_window.scrollbar_thread = QtCore.QThread()
    main_window.scrollbar_thread.start()
    main_window.scrollbar_thread_worker = Worker(main_window.setCurrentTime)
    main_window.scrollbar_thread_worker.moveToThread(main_window.scrollbar_thread)
    main_window.scrollbar_thread_worker.start.emit("start")


def plotCheckChanged(main_window, settings_window):

    # make sure that it only plots the spikes if there are sources on the GraphSettingsWindow widget
    iterator = QtGui.QTreeWidgetItemIterator(settings_window.graphs)

    source_count = 0
    while iterator.value():
        source_count += 1
        iterator += 1

    # then call the Plot function
    if source_count > 0:
        settings_window.Plot()


def run():
    app = QtGui.QApplication(sys.argv)

    # app = pg.mkQApp()

    main_w = Window()  # calling the main window

    for key, val in main_w.main_window_field_positions.items():
        if 'Import Set' in key:
            i_set_btn, j_set_btn = val
        elif 'Filename' in key:
            i_set_text, j_set_text = val

    for key, val in main_w.graph_parameter_field_positions.items():
        if 'Plot' in key:
            i_plot, j_plot = val
        elif 'Start Time' in key:
            i_start, j_start = val
        elif 'Stop Time' in key:
            i_stop, j_stop = val
        elif 'Current Time' in key:
            i_current, j_current = val

    setting_w = GraphSettingsWindows(main_w)  # calling the graph settings window

    score_w = ScoreWindow(main_w, setting_w)

    chooseSet = ChooseFile(main_w, 'Set')

    tf_plot_w = TFPlotWindow(main_w, setting_w)

    main_w.raise_()  # making the main window on top

    main_w.score_btn.clicked.connect(lambda: raise_w(score_w, main_w))
    main_w.graph_settings_btn.clicked.connect(lambda: raise_w(setting_w, main_w))
    main_w.main_window_fields[i_set_btn, j_set_btn].clicked.connect(lambda: raise_w(chooseSet, main_w, source='Set'))
    main_w.graph_parameter_fields[i_plot, j_plot+1].stateChanged.connect(lambda: plotCheckChanged(main_w, setting_w))
    # main_w.graph_parameter_fields[i_start, j_start + 1].textChanged.connect(setting_w.changeEventTimes)
    # main_w.graph_parameter_fields[i_stop, j_stop + 1].textChanged.connect(setting_w.changeEventTimes)

    chooseSet.choosebtn.clicked.connect(lambda: new_File(chooseSet, main_w, "Set"))
    chooseSet.backbtn.clicked.connect(lambda: raise_w(main_w, chooseSet))

    setting_w.hide_btn.clicked.connect(lambda: raise_w(main_w, setting_w))
    score_w.hide_btn.clicked.connect(lambda: raise_w(main_w, score_w))
    score_w.eoi_hide.clicked.connect(lambda: raise_w(main_w, score_w))

    main_w.main_window_fields[i_set_text, j_set_text + 1].textChanged.connect(functools.partial(ImportSet, main_w,
                                                                                                setting_w, score_w,
                                                                                                tf_plot_w))

    main_w.TF_btn.clicked.connect(lambda: raise_w(tf_plot_w, main_w))


    tf_plot_w.hide_btn.clicked.connect(lambda: raise_w(main_w, tf_plot_w))

    setting_w.ActiveSourceSignal.myGUI_signal.connect(tf_plot_w.updateActiveSources)
    setting_w.ActiveSourceSignal.myGUI_signal.connect(score_w.updateActiveSources)
    main_w.current_time_object = main_w.graph_parameter_fields[i_current, j_current + 1]
    main_w.start_time_object =  main_w.graph_parameter_fields[i_start, j_start + 1]
    main_w.stop_time_object =  main_w.graph_parameter_fields[i_stop, j_stop + 1]

    # hilbert_w = HilbertParametersWindow(main_w, score_w)

    setting_w.RePlotTFSignal.myGUI_signal.connect(tf_plot_w.RePlot)

    sys.exit(app.exec_())  # prevents the window from immediately exiting out


if __name__ == '__main__':
    run()  # the command that calls run()

    # import profile
    # pr = profile.Profile()
    # res = pr.run('run()')
    # res.print_stats()
