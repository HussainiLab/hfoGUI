import pyqtgraph as pg
import numpy as np
from pyqtgraph.Qt import QtCore, QtWidgets
import sys
import os
import time
import functools
from core.animal_tracking import grab_position_data
from core.GUI_Utils import background, Communicate, CustomViewBox, center, Worker, raise_w
from core.GraphSettings import GraphSettingsWindows
from core.Score import ScoreWindow
from core.TFplots import TFPlotWindow
from core.ChooseFile import ChooseFile, new_File

version = "3.0"

_author_ = "Geoffrey Barrett"  # defines myself as the author


class Window(QtWidgets.QWidget):  # defines the window class (main window)

    def __init__(self):  # initializes the main window
        super(Window, self).__init__()
        background(self)  # acquires some features from the background function we defined earlier

        pg.setConfigOption('background', '#ffffff')
        pg.setConfigOption('foreground', '#000000')

        if getattr(sys, 'frozen', False):
            # frozen
            self.setWindowTitle("hfoGUI - main window")

        else:
            # unfrozen
            self.setWindowTitle("hfoGUI - main window")

        self.ErrorDialogue = Communicate()
        self.ErrorDialogue.myGUI_signal.connect(self.PopUpMessage)

        self.scrollbar_thread = QtCore.QThread()
        self.plot_thread = QtCore.QThread()

        self.pos_plot_window = None
        self.pos_plot_widget = None
        
        # For saving last session settings
        self._settings_modified = False

        self.home()  # runs the home function

    def home(self):  # defines the home function (the main window)

        self.lr = None

        self.loaded_data = {}
        self.current_set_filename = ''  # Initialize to avoid AttributeError

        # ------ buttons + widgets -----------------------------

        self.graph_settings_btn = QtWidgets.QPushButton("Graph Settings", self)
        self.graph_settings_btn.setToolTip("Click if you want to add/remove waveforms, and edit the graph")

        self.plot_pos_btn = QtWidgets.QPushButton("Plot Trajectory", self)
        self.plot_pos_btn.setToolTip("Plot trajectory from a .pos file")

        self.score_btn = QtWidgets.QPushButton("Score", self)
        self.score_btn.setToolTip("Click if you want to score the EEG file")

        quit_btn = QtWidgets.QPushButton("Quit", self)
        quit_btn.clicked.connect(self.close_app)
        quit_btn.setShortcut("Ctrl+Q")
        quit_btn.setToolTip('Click to quit (or press Ctrl+Q)')

        self.TF_btn = QtWidgets.QPushButton("T-F Plots", self)
        self.TF_btn.setToolTip("Click to open a window showing the Time-Frequency plots (Stockwell)")

        btn_layout = QtWidgets.QHBoxLayout()

        button_order = [self.graph_settings_btn, self.plot_pos_btn, self.score_btn, self.TF_btn, quit_btn]
        for button in button_order:
            btn_layout.addWidget(button)

        # Version information -------------------------------------------
        if getattr(sys, 'frozen', False):
            version_label = QtWidgets.QLabel("hfoGUI - {}".format(version))
        else:
            version_label = QtWidgets.QLabel("hfoGUI - {}".format(version))

        # ------------- grid layout ------------------------

        self.main_window_parameters = [
            'Import Set', 'Intan Convert', 'Set Filename:', '', '', '', '',
        ]

        self.main_window_fields = {}
        self.main_window_field_positions = {}

        positions = [(i, j) for i in range(2) for j in range(7)]
        self.main_window_layout = QtWidgets.QGridLayout()

        for (i, j), parameter in zip(positions, self.main_window_parameters):

            if parameter == '':
                continue
            else:
                self.main_window_field_positions[parameter] = (i, j)
                if 'Import' in parameter or 'Intan' in parameter:
                    self.main_window_fields[i, j] = QtWidgets.QPushButton(parameter, self)
                    self.main_window_layout.addWidget(self.main_window_fields[i, j], *(i, j))

                elif 'Set Filename' in parameter:
                    self.main_window_fields[i, j] = QtWidgets.QLabel(parameter)
                    self.main_window_fields[i, j].setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    self.main_window_fields[i, j + 1] = QtWidgets.QLineEdit()
                    self.main_window_fields[i, j + 1].setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                    self.main_window_fields[i, j + 1].setText('Import a Set file!')

                    filename_layout = QtWidgets.QHBoxLayout()
                    filename_layout.addWidget(self.main_window_fields[i, j])
                    filename_layout.addWidget(self.main_window_fields[i, j + 1])
                    self.main_window_layout.addLayout(filename_layout, i, j, 1, 3)

        # ------------------- setting the graph -----------------------
        self.GraphLoaded = False
        self.source_duration = 0.0  # Initialize source duration for mouse hover display
        self.graphics_window = pg.GraphicsLayoutWidget()

        self.Graph_label = pg.LabelItem(justify='right')  # adds the Label that will be used for mouse interactions

        self.graphics_window.addItem(self.Graph_label)

        # adds the axis with custom viewbox to override the right click
        self.Graph_axis = self.graphics_window.addPlot(row=1, col=0, viewBox=CustomViewBox(self, self.graphics_window))
        self.Graph_axis.hideButtons()

        self.vb = self.Graph_axis.vb

        self.Graph_axis.setMouseEnabled(x=False, y=False)  # disables the mouse interactions

        self.Graph_axis.setLabel('bottom', "Time", units='s')  # adds the x label
        
        # Add gridlines in light color
        self.Graph_axis.showGrid(x=True, y=True, alpha=0.3)

        self.GraphLayout = QtWidgets.QVBoxLayout()
        self.GraphLayout.addLayout(self.main_window_layout)

        self.GraphLayout.addWidget(self.graphics_window)

        self.scrollbar = QtWidgets.QScrollBar(QtCore.Qt.Horizontal)

        self.scrollbar.actionTriggered.connect(functools.partial(self.changeCurrentGraph, 'scroll'))
        self.GraphLayout.addWidget(self.scrollbar)
        self.current_time = []

        # -------------- graph settigns -------------------------------

        self.graph_parameters = [
            'Window Size(ms):', '', 'Current Time(ms):', '', 'Start Time(ms):', '', 'Stop Time(ms):', '', 'Plot Spikes', '', 'Update', ''
        ]
        self.graph_parameter_fields = {}
        self.graph_parameter_field_positions = {}

        positions = [(i, j) for i in range(1) for j in range(12)]
        self.graph_parameter_layout = QtWidgets.QGridLayout()

        for (i, j), parameter in zip(positions, self.graph_parameters):

            if parameter == '':
                continue
            else:
                self.graph_parameter_field_positions[parameter] = (i, j)

                if 'Plot' in parameter:
                    self.graph_parameter_fields[i, j+1] = QtWidgets.QCheckBox(parameter)
                    self.graph_parameter_layout.addWidget(self.graph_parameter_fields[i, j + 1], i, j + 1)
                
                elif 'Update' in parameter:
                    self.update_spikes_btn = QtWidgets.QPushButton(parameter)
                    self.update_spikes_btn.setToolTip("Refresh spike display for current time window")
                    self.graph_parameter_fields[i, j+1] = self.update_spikes_btn
                    self.graph_parameter_layout.addWidget(self.graph_parameter_fields[i, j + 1], i, j + 1)

                else:

                    self.graph_parameter_fields[i, j] = QtWidgets.QLabel(parameter)
                    self.graph_parameter_layout.addWidget(self.graph_parameter_fields[i, j], *(i, j))
                    self.graph_parameter_fields[i, j + 1] = QtWidgets.QLineEdit()
                    self.graph_parameter_fields[i, j + 1].setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                    self.graph_parameter_layout.addWidget(self.graph_parameter_fields[i, j + 1], i, j+1)
                    if 'Window Size' in parameter:
                        self.i_windowsize, self.j_windowsize = (i, j)
                        self.graph_parameter_fields[i, j + 1].textChanged.connect(self.ChangeWindowSize)
                    elif 'Amplitude' in parameter:
                        pass
                    elif 'Current Time' in parameter:
                        self.i_current_time, self.j_current_time = (i, j)
                        self.graph_parameter_fields[i, j + 1].textChanged.connect(functools.partial(self.changeCurrentGraph, 'text'))
                    elif 'Start Time' in parameter or 'Stop Time' in parameter:
                        self.graph_parameter_fields[i, j + 1].textChanged.connect(self.changeEventTimes)

        # ------------- layout ------------------------------

        layout = QtWidgets.QVBoxLayout()

        layout_order = [self.GraphLayout, self.graph_parameter_layout, btn_layout]

        for order in layout_order:
            if 'Layout' in order.__str__():
                layout.addLayout(order)
                layout.addStretch(1)
            else:
                layout.addWidget(order, 0, QtCore.Qt.AlignCenter)
                layout.addStretch(1)

        layout.addStretch(1)  # adds stretch to put the version info at the bottom
        layout.addWidget(version_label)  # adds the date modification/version number

        self.setLayout(layout)

        center(self)

        self.show()
        
        # Do not auto-load last session set filename on startup
        # self._load_last_set_file()

        self.set_parameters('Default')

    def create_lr(self):

        """This method will create the linear region item which will allow the user to select/score the events
        manually"""

        self.lr = pg.LinearRegionItem()  # adding a linear region selector
        self.lr.setZValue(-10)
        self.lr.hide()  # hiding, otherwise the whole screen will be selected
        self.Graph_axis.addItem(self.lr)

    def mouseMoved(self, evt):
        pos = evt[0]  # using signal proxy turns original arguments into a tuple
        if self.Graph_axis.sceneBoundingRect().contains(pos):
            mousePoint = self.vb.mapSceneToView(pos)
            index = int(mousePoint.x())

            if index > 0 and self.source_duration is not None and self.source_duration > 0:
                self.Graph_label.setText(
                    "<span style='font-size: 12pt'>Time=%0.3f s, Total Duration: %0.1f s" % (
                    mousePoint.x(), self.source_duration))
            self.mouse_vLine.setPos(mousePoint.x())

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
        self.score_x1 = float(value1)
        self.score_x2 = float(value2)
        self.lr.show()
        self.lr.setRegion([self.score_x1/1000, self.score_x2/1000])

    def close_app(self):

        # pop up window that asks if you really want to exit the app ------------------------------------------------

        choice = QtWidgets.QMessageBox.question(self, "Quitting ",
                                            "Do you really want to exit?",
                                            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if choice == QtWidgets.QMessageBox.Yes:
            sys.exit()  # tells the app to quit
        else:
            pass

    def ChangeWindowSize(self):

        if self.GraphLoaded:
            self.get_parameters()
            self.scrollbar.setMinimum(0)
            try:
                self.scrollbar.setMaximum(int(self.SourceLength - (self.windowsize/1000 * self.SourceFs)))
            except TypeError:
                return
            self.scrollbar.setPageStep(int(self.windowsize/1000 * self.SourceFs / 3))
            self.scrollbar.setSingleStep(int(self.windowsize/1000 * self.SourceFs / 15))
            self.scrollbar.setValue(int((self.current_time/1000)*self.SourceFs))
            self.Graph_axis.setXRange(self.current_time/1000, (self.current_time + self.windowsize)/1000)
            self.Graph_axis.setYRange(0, self.graph_max)

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

        while self.GraphLoaded:
            self.get_parameters()  # sets the current time
            self.get_scroll_values()

            try:
                if self.current_time < 0:
                    pass
                try:
                    if self.previous_current_time != self.current_time:
                        self.Graph_axis.setXRange(self.current_time/1000, (self.current_time + self.windowsize)/1000, padding=0)
                        self.previous_current_time = self.current_time

                except AttributeError:
                    pass
            except TypeError:
                pass

    def update_spikes_for_window(self):
        """Refresh spike display for the current time window"""
        if not self.GraphLoaded:
            return
        # Clear previous spikes from the graph
        # This will trigger a replot of only spikes in the current window
        self.Graph_axis.clear()
        # Re-add the label and vline
        self.Graph_axis.addItem(self.Graph_label)
        self.vb = self.Graph_axis.vb
        self.mouse_vLine = pg.InfiniteLine(angle=90)
        self.Graph_axis.addItem(self.mouse_vLine, ignoreBounds=True)
        # Re-add gridlines
        self.Graph_axis.showGrid(x=True, y=True, alpha=0.3)
        # Trigger a replot by calling the Plot function
        try:
            # Access the GraphSettingsWindow instance and replot
            from core.GraphSettings import GraphSettingsWindows
            # Find the settings window - it's created in main()
            # For now, we'll just clear and let the user manually trigger via Plot button
            pass
        except:
            pass

    def get_window_indices(self):
        self.get_parameters()  # sets the current time

        window_minimum = self.current_time
        window_maximum = self.current_time + self.windowsize

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
                text = self.main_window_fields[position[0], position[1] + 1].text()
                # Don't set if it's the placeholder text or empty
                if text and text != 'Import a Set file!' and text.strip():
                    self.current_set_filename = text.strip()
                else:
                    self.current_set_filename = ''

    def get_scroll_values(self):
        try:
            self.current_time = float(self.graph_parameter_fields[self.i_current_time, self.j_current_time + 1].text())
        except (ValueError, RuntimeError):
            # ValueError: invalid text conversion, RuntimeError: widget deleted during shutdown
            self.current_time = None

        try:
            self.windowsize = float(self.graph_parameter_fields[self.i_windowsize, self.j_windowsize + 1].text())
        except (ValueError, RuntimeError):
            # ValueError: invalid text conversion, RuntimeError: widget deleted during shutdown
            self.windowsize = None

    def get_current_time(self):
        # Use Current Time field
        try:
            self.current_time = float(self.graph_parameter_fields[self.i_current_time, self.j_current_time + 1].text())
        except Exception:
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
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Bits2uV Error - No .Set File!",
                                                     "Bits2uV requires access to the .Set file for\n" +
                                                     "the appropriate parameters to convert from bits\n" +
                                                     "to micro-volts. The .Set file isn't in the directory,\n" +
                                                     "do you want hfoGUI to find the .Set file?",
                                                     QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Abort)

        elif 'NoAutoSet' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: .Set Search Error!",
                                                     "The appropriate .Set file could not be found after\n" +
                                                     "attempting to search for it through various directories,\n" +
                                                     "on this PC. Please place the .Set file in the same directory\n" +
                                                     "as the .EEG file!",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'NoScorer' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: No Scorer!",
                                                     "Before scoring please type in the 'Scorer' Field who\n" +
                                                     "is scoring this file, then you can continue!\n",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'ImportSetError' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: No Set Imported!",
                                                     "Import a '.set' file before continuing!\n",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'InvalidSourceFname' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Invalid Source filename!",
                                                     "The source filename you have chosen does not exist!\n" +
                                                     "please choose an existing filename!\n",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'NegativeCutoff' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Negative Cutoff Error!",
                                                     "Please choose positive cutoff values!\n",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'InvalidCutoff' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Invalid Cutoff!",
                                                     "The chosen cutoff is invalid!\n",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'EGFNecessary' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Cutoff Too High!",
                                                     "The EEG files are sampled at 250 Hz thus,\n" +
                                                     "the cutoff needs to be below 125 Hz!\n",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'InvalidEGFCutoff' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: EGF Cutoff Too High!",
                                                     "The EGF files are sampled at 4800 Hz thus,\n" +
                                                     "the cutoff needs to be below 2400 Hz!\n",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'ScoreFileExists' in error:

            filename = error[error.find(':')+1:]
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Score Filename Exists!",
                                                     "The filename already exists, do you want to\n" +
                                                     "overwrite this score filename!\n\n" +
                                                     "Filename: %s\n" % filename,
                                                     QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)

        elif 'MemoryError' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Memory Error!",
                                                     "This action caused a memory error!",
                                                     QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.Cancel)

        elif 'ScoreFileExistError' in error:

            filename = error[error.find(':') + 1:]
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Score Filename Doesn't Exist!",
                                                     "The filename doesn't exist there we cannot load scores,\n" +
                                                     "please score a file before trying to load it!\n\n" +
                                                     "Filename: %s\n" % filename,
                                                     QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
        elif 'InvalidDetectionParam' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Invalid Automatic Detection Parameter!",
                                                     "One of designated parameters is invalid,\n" +
                                                     "please use the correct parameter format!\n",
                                                     QtWidgets.QMessageBox.Ok)

        elif 'ZeroCutoffError' in error:
            self.choice = QtWidgets.QMessageBox.question(self, "Error: Zero Cutoff Error",
                                                     "A filter cutoff value is set to zero, this is not allowed. If you want" +
                                                     "to include zero, use a lowpass filter.",
                                                     QtWidgets.QMessageBox.Ok)

    def changeEventTimes(self):
        '''
        This method will change the Start Time and Stop Time fields, as well as plot these locations as a vertical
        line
        '''
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

        # Update the view/window based on provided Start/Stop
        try:
            if start_time is not None and stop_time is not None:
                # When both start and stop are provided, center the view on the event
                # but keep the user's window size unchanged
                event_center = (start_time + stop_time) / 2
                
                # Set the graph range using the existing window size centered on the event
                if self.windowsize is not None and self.windowsize > 0:
                    # Center the view on the event within the window size
                    view_start = max(event_center - self.windowsize / 2, 0)
                    view_end = view_start + self.windowsize
                    self.Graph_axis.setXRange(view_start/1000, view_end/1000, padding=0)
                    
                    # Update scrollbar to match the centered view
                    try:
                        self.scrollbar.setValue(int(view_start / 1000 * self.SourceFs))
                    except Exception:
                        pass
                    
                    # Update Current Time field without triggering signals (use blockSignals)
                    try:
                        current_time_field = self.graph_parameter_fields[self.i_current_time, self.j_current_time + 1]
                        current_time_field.blockSignals(True)
                        current_time_field.setText(str(view_start))
                        current_time_field.blockSignals(False)
                    except Exception:
                        pass
                else:
                    # Fallback: if no window size set, show the entire event
                    self.Graph_axis.setXRange(start_time/1000, stop_time/1000, padding=0)
                    try:
                        self.scrollbar.setValue(int(start_time / 1000 * self.SourceFs))
                    except Exception:
                        pass

            elif start_time is not None and stop_time is None:
                # Move window to start; keep current window size
                if self.windowsize is None:
                    # If windowsize missing, do not attempt range update
                    pass
                else:
                    self.Graph_axis.setXRange(start_time/1000, (start_time + self.windowsize)/1000, padding=0)
                # Sync current time field and scrollbar
                try:
                    self.graph_parameter_fields[self.i_current_time, self.j_current_time + 1].setText(str(start_time))
                except Exception:
                    pass
                try:
                    self.scrollbar.setValue(int(start_time / 1000 * self.SourceFs))
                except Exception:
                    pass

            elif start_time is None and stop_time is not None:
                # Align window end at stop; compute start from window size
                if self.windowsize is None:
                    pass
                else:
                    start_calc = max(stop_time - self.windowsize, 0)
                    self.Graph_axis.setXRange(start_calc/1000, stop_time/1000, padding=0)
                    # Sync current time field and scrollbar
                    try:
                        self.graph_parameter_fields[self.i_current_time, self.j_current_time + 1].setText(str(start_calc))
                    except Exception:
                        pass
                    try:
                        self.scrollbar.setValue(int(start_calc / 1000 * self.SourceFs))
                    except Exception:
                        pass
        except Exception:
            # Safeguard: don't break if SourceFs/Graph not ready
            pass

        if start_time is not None:

            try:
                # self.start_line.remove()
                self.Graph_axis.removeItem(self.start_line)
            except:
                pass

            self.start_line = pg.InfiniteLine(pos=start_time/1000, angle=90, pen=(255, 0, 0))

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

            self.stop_line = pg.InfiniteLine(pos=stop_time/1000, angle=90,
                                              pen=(0, 255, 0))

            self.Graph_axis.addItem(self.stop_line)
        else:
            try:
                self.stop_line.remove()
            except:
                pass

    def plot_pos_trajectory(self, event_points=None):
        """Plot only the trajectory from an Axona .pos file in a simple 2D view.
        Optionally overlay detected event points as red dots.
        Args:
            event_points: Optional, Nx2 array-like of (x, y) event positions to overlay.
        """
        if isinstance(event_points, bool):
            event_points = None

        def _get_ppm_from_graph_settings():
            fallback_ppm = 511
            gs = getattr(self, 'graph_settings_window', None)
            if gs is None:
                return fallback_ppm

            for option, (i, j) in gs.graph_header_option_positions.items():
                if 'PPM (pixels/meter)' in option:
                    try:
                        text = gs.graph_header_option_fields[i, j + 1].text()
                    except Exception:
                        return fallback_ppm

                    if text is None:
                        return fallback_ppm
                    text = text.strip()
                    if not text:
                        return fallback_ppm
                    try:
                        ppm_val = float(text)
                        return ppm_val
                    except ValueError:
                        return fallback_ppm
            return fallback_ppm

        ppm_value = _get_ppm_from_graph_settings()

        # Try to infer the .pos path from the current .set, otherwise ask the user
        inferred_path = None
        if getattr(self, 'current_set_filename', ''):
            base = os.path.splitext(self.current_set_filename)[0]
            candidate = f"{base}.pos"
            if os.path.exists(candidate):
                inferred_path = candidate

        if inferred_path is None:
            start_dir = os.path.dirname(self.current_set_filename) if getattr(self, 'current_set_filename', '') else ''
            pos_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self,
                "Select .pos file",
                start_dir,
                "Axona pos (*.pos)"
            )
            if not pos_path:
                return
        else:
            pos_path = inferred_path

        try:
            pos_x, pos_y, pos_t, _ = grab_position_data(pos_path, ppm_value)
        except Exception as exc:  # pylint: disable=broad-except
            QtWidgets.QMessageBox.critical(
                self,
                "Position Plot Error",
                f"Failed to load trajectory from:\n{pos_path}\n\n{exc}"
            )
            return

        x = np.asarray(pos_x).flatten()
        y = np.asarray(pos_y).flatten()
        t_pos = np.asarray(pos_t).flatten()

        # If event_points are given in time indices, map to x/y
        event_x = event_y = None

        # If no events provided, try to fetch from ScoreWindow (Automated Detection)
        if event_points is None and hasattr(self, 'score_window'):
            eoi_list = []
            if self.score_window.EOI.topLevelItemCount() > 0:
                # Find start time column
                start_col = -1
                for key, val in self.score_window.EOI_headers.items():
                    if 'Start Time' in key:
                        start_col = val
                        break
                
                if start_col != -1:
                    for i in range(self.score_window.EOI.topLevelItemCount()):
                        item = self.score_window.EOI.topLevelItem(i)
                        try:
                            # Time is in ms, convert to seconds
                            t_ms = float(item.text(start_col))
                            eoi_list.append(t_ms / 1000.0)
                        except ValueError:
                            continue
            
            if eoi_list and t_pos.size > 0:
                # Map event times to closest position indices
                indices = np.searchsorted(t_pos, eoi_list)
                indices = np.clip(indices, 0, len(t_pos) - 1)
                event_points = np.column_stack((x[indices], y[indices]))

        if event_points is not None:
            event_points = np.asarray(event_points)
            if event_points.ndim == 2 and event_points.shape[1] == 2:
                event_x, event_y = event_points[:, 0], event_points[:, 1]

        if x.size == 0 or y.size == 0:
            QtWidgets.QMessageBox.information(
                self,
                "Position Plot",
                "No position samples were found in the selected .pos file."
            )
            return


        title_ppm = f".pos Trajectory  (PPM: {ppm_value})"
        if self.pos_plot_window is None:
            self.pos_plot_window = QtWidgets.QDialog(self)
            self.pos_plot_window.setWindowTitle(title_ppm)
            layout = QtWidgets.QVBoxLayout(self.pos_plot_window)
            self.pos_plot_widget = pg.PlotWidget()
            layout.addWidget(self.pos_plot_widget)
        else:
            self.pos_plot_window.setWindowTitle(title_ppm)


        self.pos_plot_widget.clear()
        # Plot trajectory in gray
        self.pos_plot_widget.plot(x, y, pen=pg.mkPen(color=(150, 150, 150), width=1))
        # Overlay detected event points as red dots
        if event_x is not None and event_y is not None:
            self.pos_plot_widget.plot(event_x, event_y, pen=None, symbol='o', symbolBrush=(255,0,0), symbolSize=10, name='Detected Events')
        self.pos_plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.pos_plot_widget.setLabel('bottom', 'X (cm)')
        self.pos_plot_widget.setLabel('left', 'Y (cm)')
        self.pos_plot_widget.setAspectLocked(True)
        self.pos_plot_widget.enableAutoRange()

        # --- Add 4x4 bin grid overlay and bin counts ---
        n_bins = 4
        # Compute bin edges
        x_min, x_max = np.nanmin(x), np.nanmax(x)
        y_min, y_max = np.nanmin(y), np.nanmax(y)
        x_edges = np.linspace(x_min, x_max, n_bins + 1)
        y_edges = np.linspace(y_min, y_max, n_bins + 1)
        # Draw grid lines
        for xe in x_edges:
            self.pos_plot_widget.addLine(x=xe, pen=pg.mkPen(color=(0, 0, 255, 100), width=1, style=QtCore.Qt.DashLine))
        for ye in y_edges:
            self.pos_plot_widget.addLine(y=ye, pen=pg.mkPen(color=(0, 0, 255, 100), width=1, style=QtCore.Qt.DashLine))

        # Bin the trajectory points
        H, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges])
        # Optionally, annotate bin counts
        for i in range(n_bins):
            for j in range(n_bins):
                # Center of each bin
                xc = (x_edges[i] + x_edges[i+1]) / 2
                yc = (y_edges[j] + y_edges[j+1]) / 2
                count = int(H[i, j])
                if count > 0:
                    text = pg.TextItem(text=str(count), color=(200, 0, 0), anchor=(0.5, 0.5))
                    self.pos_plot_widget.addItem(text)
                    text.setPos(xc, yc)



        # Alternative: Use image moments to assess shape
        import cv2
        import matplotlib.pyplot as plt
        # Normalize and scale trajectory to image
        img_size = 256
        x_img = ((x - np.nanmin(x)) / (np.nanmax(x) - np.nanmin(x)) * (img_size - 1)).astype(np.int32)
        y_img = ((y - np.nanmin(y)) / (np.nanmax(y) - np.nanmin(y)) * (img_size - 1)).astype(np.int32)
        img = np.zeros((img_size, img_size), dtype=np.uint8)
        for xi, yi in zip(x_img, y_img):
            img[yi, xi] = 255
        # Find contours
        contours, _ = cv2.findContours(img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        arena_shape = "unknown"
        if contours:
            cnt = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(cnt)
            perimeter = cv2.arcLength(cnt, True)
            # Circularity: 4*pi*area / perimeter^2
            if perimeter > 0:
                circularity = 4 * np.pi * area / (perimeter ** 2)
                if circularity > 0.7:
                    arena_shape = "circle"
                else:
                    arena_shape = "box"
        # Optionally, plot for debugging
        # plt.imshow(img, cmap='gray')
        # plt.title(f"Arena shape: {arena_shape}, circularity={circularity:.2f}")
        # plt.show()

        # Show arena shape in window title
        self.pos_plot_window.setWindowTitle(f".pos Trajectory  (PPM: {ppm_value}, Arena: {arena_shape})")

        self.pos_plot_window.show()
        self.pos_plot_window.raise_()
        self.pos_plot_window.activateWindow()

    def _load_last_set_file(self):
        """Load the last used set file/folder from settings"""
        import json
        settings_file = os.path.join(self.SETTINGS_DIR, 'last_session.json')
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    data = json.load(f)
                    last_file = data.get('last_set_file')
                    if last_file and os.path.exists(last_file):
                        for key, val in self.main_window_field_positions.items():
                            if 'Set Filename' in key:
                                i_set_text, j_set_text = val
                                self.main_window_fields[i_set_text, j_set_text + 1].setText(last_file)
                                break
        except Exception:
            pass

    def _save_last_set_file(self):
        """Save the current set file/folder to settings"""
        import json
        try:
            for key, val in self.main_window_field_positions.items():
                if 'Set Filename' in key:
                    i_set_text, j_set_text = val
                    current_file = self.main_window_fields[i_set_text, j_set_text + 1].text()
                    if current_file and current_file != 'Import a Set file!':
                        settings_file = os.path.join(self.SETTINGS_DIR, 'last_session.json')
                        with open(settings_file, 'w') as f:
                            json.dump({'last_set_file': current_file}, f)
                    break
        except Exception:
            pass

    def closeEvent(self, event):
        """Override close event to save settings and stop worker threads"""
        # Stop the scrollbar worker thread to prevent accessing deleted widgets
        self.GraphLoaded = False
        if hasattr(self, 'scrollbar_thread') and self.scrollbar_thread.isRunning():
            self.scrollbar_thread.quit()
            self.scrollbar_thread.wait(1000)  # Wait up to 1 second for thread to finish
        
        self._save_last_set_file()
        super().closeEvent(event)


def clear_all(main_window, graph_options_window, score_window, tf_plots_window):
    main_window.loaded_data = {}
    main_window.current_time = 0

    graph_options_window.loaded_sources = {}
    graph_options_window.cell_spike_time_array = []
    graph_options_window.cell_labels = []
    main_window.GraphLoaded = False

    main_window.Graph_axis.clear()

    # clear current scores
    score_window.scores.clear()
    score_window.EOI.clear()
    score_window.initialize_attributes()

    graph_options_window.graphs.clear()
    graph_options_window.FilterResponseAxis.clear()
    graph_options_window.FilterResponseCanvas.draw()
    graph_options_window.initialize_attributes()

    tf_plots_window.clearPlots()


def run_intan_converter():
    """Run the Intan RHD to Tint format converter script"""
    try:
        # Get the directory where intan_rhd_format.py is located (same directory as main.py)
        script_path = os.path.join(os.path.dirname(__file__), 'intan_rhd_format.py')
        
        # Run the script in a subprocess
        import subprocess
        subprocess.Popen([sys.executable, script_path])
    except Exception as e:
        print(f"Error running Intan converter: {e}")


def ImportSet(main_window, graph_options_window, score_window, tf_plots_window):
    """Updates the fields of the graph options window when the .set file changes"""
    if hasattr(main_window, 'scrollbar_thread'):
        main_window.scrollbar_thread.terminate()

    main_window.set_current_filename()  # update the new filename

    # update the parameters from the Main Window
    main_window.get_parameters()

    # Loading from either a Set file or a folder

    # If a folder was provided, find the "top-most" .set file within that folder
    if isinstance(main_window.current_set_filename, str) and os.path.isdir(main_window.current_set_filename):
        folder = main_window.current_set_filename
        try:
            entries = os.listdir(folder)
        except (FileNotFoundError, PermissionError):
            return

        set_candidates = sorted([f for f in entries if f.lower().endswith('.set')])
        if len(set_candidates) == 0:
            # No .set found in folder; cannot proceed
            return

        # Pick the first alphabetically as the "top-most" .set
        chosen_set = set_candidates[0]
        chosen_set_path = os.path.join(folder, chosen_set)

        # Update the Main window field to the discovered .set path; will retrigger ImportSet
        for key, val in main_window.main_window_field_positions.items():
            if 'Set Filename' in key:
                i_set_text, j_set_text = val
                break
        current_text = main_window.main_window_fields[i_set_text, j_set_text + 1].text()
        if os.path.realpath(current_text) != os.path.realpath(chosen_set_path):
            main_window.main_window_fields[i_set_text, j_set_text + 1].setText(os.path.realpath(chosen_set_path))
        return

    # Otherwise expect a .set or .egf file path
    desired_set_extgension = ['.set', '.egf']
    if main_window.current_set_filename == '' or all(ext not in main_window.current_set_filename.lower() for ext in desired_set_extgension):
        return

    set_basename = os.path.basename(os.path.splitext(main_window.current_set_filename)[0])
    set_directory = os.path.dirname(main_window.current_set_filename)

    # finding EEG/EGF files and LFP files within the same directory
    try:
        directory_file_list = os.listdir(set_directory)
    except FileNotFoundError:
        return
    except PermissionError:
        return

    eeg_files = [file for file in directory_file_list if (set_basename in file)and ('.eeg' in file or '.egf' in file)]
    lfp_files = []
    main_window.active_tetrodes = []

    invalid_types = ['.clu', '.eeg', '.egf', '.set', '.cut', '.fmask', '.fet', '.klg', '.pos', '.SET', '.ini', '.txt']
    lfp_files = [file for file in directory_file_list
                if not any(x in file for x in invalid_types) and not os.path.isdir(os.path.join(set_directory, file))
                and any('%s.%d' % (set_basename, i) in file for i in range(1, 257))]

    pos_files = [file for file in directory_file_list if set_basename+'.pos' in file or set_basename+'.egf' in file]

    source_files = eeg_files + pos_files

    [main_window.active_tetrodes.append(int((os.path.splitext(file)[1])[1:])) for file in lfp_files]
    for option, position in graph_options_window.graph_header_option_positions.items():
        if 'source' in option.lower():
            i, j = position # found the Source combobox in the Graph Settings Window
            break

    graph_combobox = graph_options_window.graph_header_option_fields[i, j + 1]
    graph_combobox.clear()

    graph_options_window.source_extensions = []

    # This will add the "sources" for the graph settings window
    for file in source_files:
        file_extension = os.path.splitext(file)[-1]
        if '.pos' not in file_extension:
            graph_combobox.addItem(file_extension)
        else:
            graph_combobox.addItem('Speed')

    # Auto-select preferred source: EGF if available, else EEG
    preferred_index = -1
    egf_index = graph_combobox.findText('.egf')
    if egf_index != -1:
        preferred_index = egf_index
    else:
        eeg_index = graph_combobox.findText('.eeg')
        if eeg_index != -1:
            preferred_index = eeg_index
    if preferred_index != -1:
        graph_combobox.setCurrentIndex(preferred_index)
        # Auto-add the selected source to the graphs list
        try:
            graph_options_window.validateSource('add')
        except Exception:
            pass

    # replace the score with a new proper score file
    score_filename = os.path.join(set_directory, 'HFOScores', set_basename, '%s_HFOScores.txt' % set_basename)
    score_window.score_filename.setText(score_filename)

    score_window.setEOIfilename()

    clear_all(main_window, graph_options_window, score_window, tf_plots_window)

    main_window.scrollbar_thread.start()
    main_window.scrollbar_thread_worker = Worker(main_window.setCurrentTime)
    main_window.scrollbar_thread_worker.moveToThread(main_window.scrollbar_thread)
    main_window.scrollbar_thread_worker.start.emit("start")


def plotCheckChanged(main_window, settings_window):

    # make sure that it only plots the spikes if there are sources on the GraphSettingsWindow widget
    iterator = QtWidgets.QTreeWidgetItemIterator(settings_window.graphs)

    source_count = 0
    while iterator.value():
        source_count += 1
        iterator += 1

    # then call the Plot function
    if source_count > 0:
        settings_window.Plot()


def run():
    app = QtWidgets.QApplication(sys.argv)

    main_w = Window()  # calling the main window

    for key, val in main_w.main_window_field_positions.items():
        if 'Import Set' in key:
            i_set_btn, j_set_btn = val
        elif 'Intan Convert' in key:
            i_intan_btn, j_intan_btn = val
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
    main_w.graph_settings_window = setting_w

    score_w = ScoreWindow(main_w, setting_w)
    main_w.score_window = score_w

    chooseSet = ChooseFile(main_w, 'Set')

    tf_plot_w = TFPlotWindow(main_w, setting_w)

    main_w.raise_()  # making the main window on top

    main_w.score_btn.clicked.connect(lambda: raise_w(score_w, main_w))
    main_w.graph_settings_btn.clicked.connect(lambda: raise_w(setting_w, main_w))
    main_w.plot_pos_btn.clicked.connect(main_w.plot_pos_trajectory)
    main_w.main_window_fields[i_set_btn, j_set_btn].clicked.connect(lambda: raise_w(chooseSet, main_w, source='Set'))
    main_w.main_window_fields[i_intan_btn, j_intan_btn].clicked.connect(run_intan_converter)
    main_w.graph_parameter_fields[i_plot, j_plot+1].stateChanged.connect(lambda: plotCheckChanged(main_w, setting_w))

    # Connect Update Spikes button
    if hasattr(main_w, 'update_spikes_btn'):
        main_w.update_spikes_btn.clicked.connect(lambda: plotCheckChanged(main_w, setting_w))

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

    setting_w.RePlotTFSignal.myGUI_signal.connect(tf_plot_w.RePlot)

    sys.exit(app.exec_())  # prevents the window from immediately exiting out


if __name__ == '__main__':
    run()  # the command that calls run()
