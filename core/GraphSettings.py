from PyQt4 import QtCore, QtGui
from core.GUI_Utils import *
import os, time, json, functools, datetime
from scipy.signal import hilbert
import matplotlib
# matplotlib.use("Qt4Agg")
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt
import numpy as np
import core.SignalProcessing as sp
import scipy.signal as signal
import scipy
import pyqtgraph as pg


class update_plots_signal(QtCore.QObject):

    # mysignal = QtCore.pyqtSignal(object, object, object)
    mysignal = QtCore.pyqtSignal(str, object, object, dict)

    # could have combined these two into a single signal... but who has time for that?
    mouse_signal = QtCore.pyqtSignal(str)
    lr_signal = QtCore.pyqtSignal(str)


class customProgress_signal(QtCore.QObject):
    start_signal = QtCore.pyqtSignal(str)
    mysignal = QtCore.pyqtSignal(str, dict)
    close_signal = QtCore.pyqtSignal(str)


class GraphSettingsWindows(QtGui.QWidget):
    """This is going to be the QWidget class that will be the popup window if the user
    decides they want to add a Graph, this will handle all graphing on the main QWidget as well"""

    def __init__(self, main):
        super(GraphSettingsWindows, self).__init__()
        background(self)
        width = self.deskW / 4.2
        height = self.deskH / 1.5

        self.newData = update_plots_signal()
        self.newData.mysignal.connect(self.update_plots)
        self.newData.mouse_signal.connect(self.mouse_slot)

        self.progress_signal = customProgress_signal()
        self.progress_signal.start_signal.connect(lambda: self.Progress('start'))
        self.progress_signal.mysignal.connect(self.update_progress)
        self.progress_signal.close_signal.connect(lambda: self.Progress('stop'))

        self.ActiveSourceSignal = Communicate()
        self.RePlotTFSignal = Communicate()

        self.profile_filename = os.path.join(main.SETTINGS_DIR, 'profiles.json')

        self.mainWindow = main

        self.initialize_attributes()

        self.newData.lr_signal.connect(self.mainWindow.create_lr)

        self.mainWindow.vb.mouseDragEvent = self.drag  # overriding the drag event

        self.mainWindow.graphics_window.scene().sigMouseClicked.connect(self.mousePress)
        # self.mainWindow.graphics_window.scene().sigMouseDragged.connect(self.mouseDrag)

        self.setWindowTitle("hfoGUI - Graph Settings Window")  # sets the title of the window

        main_location = main.frameGeometry().getCoords()
        # self.show()
        self.setGeometry(main_location[2] - 1.5*main_location[-1] - 45, main_location[1] + 30, width, height)

        self.FilterResponse = plt.figure(figsize=(3, 3))
        self.FilterResponseCanvas = FigureCanvas(self.FilterResponse)
        self.FilterResponseAxis = self.FilterResponse.add_axes([0.1, 0.2, 0.85, 0.75], frameon=False)
        # self.FilterResponseToolBar = NavigationToolbar(self.FilterResponseCanvas, self)

        FilterResponseLabel = QtGui.QLabel('Filter Response:')
        FilterResponse = QtGui.QVBoxLayout()

        for filter_widget in [FilterResponseLabel, self.FilterResponseCanvas]:
            FilterResponse.addWidget(filter_widget)

        # --------- widgets ---------------------

        self.graphs = QtGui.QTreeWidget()
        self.graphs.itemSelectionChanged.connect(self.sourceSelected)
        # self.graphs.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)
        #  allowing the selection of multiple scores
        self.graph_header_options = ['Load Data Profile:', '', 'Save Profile', '', '', '',
                                     'Source:', '', 'Filter Method:', '', 'Filter Type:', '',
                                     'Filter Order', '', 'Lower Cutoff (Hz):', '', 'Upper Cutoff (Hz):', '',
                                     'Notch Filter (Hz):', '', 'Mark Peaks', '', 'Gain (V/V):', '',
                                     'Arena:', '', 'Hilbert:', '', '', '']

        self.graph_header_option_fields = {}
        self.graph_header_option_positions = {}

        positions = [(i, j) for i in range(5) for j in range(6)]
        self.graph_header_option_layout = QtGui.QGridLayout()

        for (i, j), parameter in zip(positions, self.graph_header_options):

            if parameter == '':
                continue
            else:
                self.graph_header_option_positions[parameter] = (i, j)

                if any((x in parameter for x in ['Filter Type:', 'Arena', 'Filter Method', 'Source', 'Notch', 'Mark',
                                                 'Load Data Profile'])):
                    self.graph_header_option_fields[i, j] = QtGui.QLabel(parameter)
                    self.graph_header_option_fields[i, j + 1] = QtGui.QComboBox()
                    self.graph_header_option_fields[i, j + 1].setEditable(True)
                    self.graph_header_option_fields[i, j + 1].lineEdit().setReadOnly(True)
                    self.graph_header_option_fields[i, j + 1].lineEdit().setAlignment(QtCore.Qt.AlignHCenter)
                    self.graph_header_option_fields[i, j + 1].setSizePolicy(QtGui.QSizePolicy(
                        QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))
                    if 'Filter Type' in parameter:
                        options = ['None', 'Low Pass', 'High Pass', 'Bandpass']

                    elif 'Filter Method' in parameter:
                        options = ['butter', 'fftbandpass', 'cheby1', 'cheby2', 'ellip', 'bessel']

                    elif 'Source' in parameter:
                        options = ['Import .Set!']

                    elif 'Notch' in parameter:
                        options = ['None', '60 Hz', '50 Hz']

                    elif 'Mark' in parameter:
                        options = ['No', 'Yes']

                    elif 'Arena' in parameter:
                        options = ['DarkRoom', 'BehaviorRoom', 'Room4', 'Circular Track',
                                   'Simple Circular Track', 'Four Leaf Clover Track']

                    elif 'Load Data Profile' in parameter:
                        options = ['None']
                        self.current_profile = 'None'
                        # self.graph_header_option_fields[i, j + 1].currentIndexChanged.connect(self.changeProfile)
                        try:
                            with open(self.profile_filename, 'r+') as f:
                                profiles = json.load(f)
                            options.extend(sorted(list(profiles.keys())))
                        except FileNotFoundError:
                            pass

                    for option_value in options:
                        self.graph_header_option_fields[i, j + 1].addItem(option_value)

                    if 'Filter Type' in parameter:
                        self.graph_header_option_fields[i, j + 1].currentIndexChanged.connect(
                            functools.partial(self.changeFilter, i, j))

                    if 'Filter Method' in parameter:
                        self.graph_header_option_fields[i, j + 1].currentIndexChanged.connect(
                            functools.partial(self.changeMethod, i, j))

                    combobox_layout = QtGui.QHBoxLayout()
                    combobox_layout.addWidget(self.graph_header_option_fields[i, j])
                    combobox_layout.addWidget(self.graph_header_option_fields[i, j + 1])
                    self.graph_header_option_layout.addLayout(combobox_layout, *(i, j))

                elif 'Cutoff' in parameter:
                    self.graph_header_option_fields[i, j] = QtGui.QLabel(parameter)
                    self.graph_header_option_fields[i, j].setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    # self.main_window_layout.addWidget(self.main_window_fields[i, j], *(i, j))
                    self.graph_header_option_fields[i, j + 1] = QtGui.QLineEdit()
                    self.graph_header_option_fields[i, j + 1].setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                    self.graph_header_option_fields[i, j + 1].setDisabled(1)
                    self.graph_header_option_fields[i, j + 1].setText('N/A')

                    cutoff_layout = QtGui.QHBoxLayout()
                    cutoff_layout.addWidget(self.graph_header_option_fields[i, j])
                    cutoff_layout.addWidget(self.graph_header_option_fields[i, j + 1])
                    self.graph_header_option_layout.addLayout(cutoff_layout, *(i, j))

                elif 'Order' in parameter:
                    self.graph_header_option_fields[i, j] = QtGui.QLabel(parameter)
                    self.graph_header_option_fields[i, j].setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    # self.main_window_layout.addWidget(self.main_window_fields[i, j], *(i, j))
                    self.graph_header_option_fields[i, j + 1] = QtGui.QLineEdit()
                    self.graph_header_option_fields[i, j + 1].setAlignment(
                        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)
                    # self.graph_header_option_fields[i, j + 1].setDisabled(1)
                    self.graph_header_option_fields[i, j + 1].setText('3')

                    Order_layout = QtGui.QHBoxLayout()
                    Order_layout.addWidget(self.graph_header_option_fields[i, j])
                    Order_layout.addWidget(self.graph_header_option_fields[i, j + 1])
                    self.graph_header_option_layout.addLayout(Order_layout, *(i, j))

                elif 'Gain' in parameter:

                    self.graph_header_option_fields[i, j] = QtGui.QLabel(parameter)
                    self.graph_header_option_fields[i, j].setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
                    # self.main_window_layout.addWidget(self.main_window_fields[i, j], *(i, j))
                    self.graph_header_option_fields[i, j + 1] = QtGui.QLineEdit()
                    self.graph_header_option_fields[i, j + 1].setText('1')
                    self.graph_header_option_fields[i, j + 1].setAlignment(
                        QtCore.Qt.AlignCenter | QtCore.Qt.AlignVCenter)

                    gain_layout = QtGui.QHBoxLayout()
                    gain_layout.addWidget(self.graph_header_option_fields[i, j])
                    gain_layout.addWidget(self.graph_header_option_fields[i, j + 1])
                    self.graph_header_option_layout.addLayout(gain_layout, *(i, j))

                elif 'Save' in parameter:
                    self.save_profile_btn = QtGui.QPushButton('Save Profile')
                    self.save_profile_btn.clicked.connect(self.saveProfile)
                    # self.graph_header_option_layout.addWidget(self.save_profile_btn, *(i, j))

                    self.load_profile_btn = QtGui.QPushButton('Load Profile')
                    self.load_profile_btn.clicked.connect(self.changeProfile)

                    self.delete_profile_btn = QtGui.QPushButton('Delete Profile')
                    self.delete_profile_btn.clicked.connect(self.deleteProfile)

                    button_layout = QtGui.QHBoxLayout()
                    button_layout.addWidget(self.load_profile_btn)
                    button_layout.addWidget(self.save_profile_btn)
                    button_layout.addWidget(self.delete_profile_btn)

                    self.graph_header_option_layout.addLayout(button_layout, i, j, i + 1, j + 1)

                elif 'Hilbert' in parameter:
                    self.graph_header_option_fields[i, j + 1] = QtGui.QCheckBox(parameter[:-1])
                    self.graph_header_option_layout.addWidget(self.graph_header_option_fields[i, j + 1], *(i, j))

        header_option_layout = QtGui.QHBoxLayout()
        option_index = 0
        for option in self.graph_header_options:
            if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                continue
            option_layout = QtGui.QHBoxLayout()
            self.option_field = option
            self.graphs.headerItem().setText(option_index, option)
            option_index += 1

        # ------------------------------button layout --------------------------------------
        self.hide_btn = QtGui.QPushButton('Hide', self)
        self.add_btn = QtGui.QPushButton('Add Graph Source', self)
        self.add_btn.clicked.connect(functools.partial(self.validateSource, 'add'))
        self.update_btn = QtGui.QPushButton('Update Selected Graph Source', self)
        self.update_btn.clicked.connect(functools.partial(self.validateSource, 'update'))
        self.remove_btn = QtGui.QPushButton('Remove Selected Graph Source', self)
        self.remove_btn.clicked.connect(self.removeSource)
        self.plot_resp = QtGui.QPushButton('Plot Filter Response', self)
        self.plot_resp.clicked.connect(self.plot_response)

        btn_layout = QtGui.QHBoxLayout()

        for button in [self.add_btn, self.plot_resp, self.update_btn, self.remove_btn, self.hide_btn]:
            btn_layout.addWidget(button)
        # ------------------ layout ------------------------------

        layout_order = [self.graphs, FilterResponse, self.graph_header_option_layout, btn_layout]

        layout_score = QtGui.QVBoxLayout()
        # layout_score.addStretch(1)
        for order in layout_order:
            if 'Layout' in order.__str__():
                layout_score.addLayout(order)
                # layout_score.addStretch(1)
            else:
                # layout_score.addWidget(order, 0, QtCore.Qt.AlignCenter)
                layout_score.addWidget(order)
                # layout_score.addStretch(1)

        self.setDefaultOptions()
        self.setLayout(layout_score)

    def drag(self, ev):
        # global vb, lr
        if (ev.button() == QtCore.Qt.LeftButton):
            self.mainWindow.lr.show()  # showing the linear region selector

            # defining the selected region
            self.mainWindow.lr.setRegion([self.mainWindow.vb.mapToView(ev.buttonDownPos()).x(), self.mainWindow.vb.mapToView(ev.pos()).x()])
            self.mainWindow.score_x1 = self.mainWindow.vb.mapToView(ev.buttonDownPos()).x()  # defining the start of the selected region
            self.mainWindow.score_x2 = self.mainWindow.vb.mapToView(ev.pos()).x()  # defining the end of the selected region

            if hasattr(self, 'lines'):
                if self.selected_time is not None:
                    try:
                        # self.lines.remove()
                        # remove old lines that were created
                        self.mainWindow.Graph_axis.removeItem(self.lines)
                        self.selected_time = None
                    except:
                        pass

            ev.accept()
        else:
            pg.ViewBox.mouseDragEvent(self.mainWindow.vb, ev)

    def initialize_attributes(self):
        self.active_sources = []

        self.mainWindow.source_duration = None

        self.selected_time = None

        self.plotting = False
        self.loaded_sources = {}
        self.cell_spike_time_array = []
        self.cell_labels = []

    def Progress(self, string):

        if 'start' in string:
            self.progress_value = 0
            self.progdialog = QtGui.QProgressDialog(
                "Plotting Sources...", "Cancel", 0, 100, self)
            self.progdialog.setWindowTitle("Plotting")
            self.progdialog.setWindowModality(QtCore.Qt.WindowModal)
            self.progdialog.show()
            self.progdialog.setValue(0)
        elif 'stop' in string:
            self.progdialog.close()

    def update_progress(self, action, kwargs):

        if 'setText' in action:

            self.progdialog.setLabelText(kwargs['text'])

        elif 'setValue' in action:

            self.progdialog.setValue(kwargs['value'])

    def plot_response(self):

        # get the filter parameters
        for parameter, (i, j) in self.graph_header_option_positions.items():
            if 'Filter Method' in parameter:
                filttype = self.graph_header_option_fields[i, j + 1].currentText()
            elif 'Filter Order' in parameter:
                order = int(self.graph_header_option_fields[i, j + 1].text())
            elif 'Filter Type' in parameter:
                bandtype = self.graph_header_option_fields[i, j + 1].currentText()

            elif 'Lower Cutoff' in parameter:
                try:
                    lower_cutoff = float(self.graph_header_option_fields[i, j + 1].text())
                except ValueError:
                    try:
                        lower_cutoff = int(self.graph_header_option_fields[i, j + 1].text())
                    except:
                        lower_cutoff = None
                i_lower = i
                j_lower = j

            elif 'Upper Cutoff' in parameter:
                try:
                    upper_cutoff = float(self.graph_header_option_fields[i, j + 1].text())
                except ValueError:
                    try:
                        upper_cutoff = int(self.graph_header_option_fields[i, j + 1].text())
                    except:
                        upper_cutoff = None

                i_upper = i
                j_upper = j
            elif 'Source' in parameter:
                source = self.graph_header_option_fields[i, j + 1].currentText()

        if 'Import' in source:
            return
        else:
            if '.eeg' in source:
                Fs = 250
            elif '.egf' in source:
                Fs = 4.8e3

        if order > 4.8e3:
            # large Fs will cause problems with lower frequencies
            pass

        self.FilterResponseAxis.clear()  # clearing the current plot

        if upper_cutoff is not None:
            if upper_cutoff > Fs/2:
                upper_cutoff = Fs/2
                self.graph_header_option_fields[i_upper, j_upper + 1].setText(str(upper_cutoff))

        if lower_cutoff is not None:
            if lower_cutoff < 0:
                lower_cutoff = 0
                self.graph_header_option_fields[i_lower, j_lower + 1].setText(str(lower_cutoff))

        if 'fft' not in filttype:
            analog_val = False

            if 'Band' in bandtype:

                if upper_cutoff >= Fs/2 and lower_cutoff <= 0:
                    pass

                elif upper_cutoff >= Fs/2:
                    b, a = sp.Filtering.iirfilt(self, 'high', [], Fs, Wp=lower_cutoff, Ws=[], order=order,
                                                analog_val=False, Rp=0.1, As=60, filttype=filttype, output='b-a')

                elif lower_cutoff <= 0:
                    b, a = sp.Filtering.iirfilt(self, 'low', [], Fs, Wp=upper_cutoff, Ws=[], order=order,
                                                analog_val=False, Rp=0.1, As=60, filttype=filttype, output='b-a')
                else:
                    b, a = sp.Filtering.iirfilt(self, 'band', [], Fs, Wp=lower_cutoff, Ws=upper_cutoff, order=order,
                                                analog_val=False, Rp=0.1, As=60, filttype=filttype, output='b-a')
            elif 'Low' in bandtype:
                b, a = sp.Filtering.iirfilt(self, 'low', [], Fs, Wp=upper_cutoff, Ws=[], order=order, analog_val=False,
                                            Rp=0.1, As=60, filttype=filttype, output='b-a')
                lower_cutoff = None
            elif 'High' in bandtype:
                b, a = sp.Filtering.iirfilt(self, 'high', [], Fs, Wp=lower_cutoff, Ws=[], order=order, analog_val=False,
                                            Rp=0.1, As=60, filttype=filttype, output='b-a')
                upper_cutoff = None
            else:
                return

            if not analog_val:
                w, h = signal.freqz(b, a, worN=8000)  # returns the requency response h, and the normalized angular
                # frequencies w in radians/sample
                # w (radians/sample) * Fs (samples/sec) * (1 cycle/2pi*radians) = Hz
                f = Fs * w / (2 * np.pi)  # Hz
            else:
                w, h = signal.freqs(b, a, worN=8000)  # returns the requency response h,
                # and the angular frequencies w in radians/sec
                # w (radians/sec) * (1 cycle/2pi*radians) = Hz
                f = w / (2 * np.pi)  # Hz

            # plt.figure(figsize=(10, 5))
            # plt.subplot(211)
            self.FilterResponseAxis.semilogx(f, np.abs(h), 'b')
            self.FilterResponseAxis.set_xscale('log')
            # self.FilterResponseAxis.margins(0, 0.1)

            if 'low' in bandtype.lower():
                self.FilterResponseAxis.axvline(upper_cutoff, color='green')
                # self.FilterResponseAxis.set_xlim(0.01, 2 * upper_cutoff)
            elif 'high' in bandtype.lower():
                self.FilterResponseAxis.axvline(lower_cutoff, color='green')
                # self.FilterResponseAxis.set_xlim(0.01, 2 * lower_cutoff)
            else:
                self.FilterResponseAxis.axvline(upper_cutoff, color='green')
                self.FilterResponseAxis.axvline(lower_cutoff, color='green')
                # #elf.FilterResponseAxis.set_xlim(0.01, 2 * upper_cutoff)

                # plt.plot(cutoff, 0.5*np.sqrt(2), 'ko') # cutoff frequency

        else:
            # get the response of an arbitrary 10 seconds worth of data
            Fs1 = lower_cutoff - 1
            if Fs1 <= 0:
                Fs1 = 0.1

                if Fs1 >= lower_cutoff:
                    lower_cutoff = Fs1 + 0.1
                    self.graph_header_option_fields[i_lower, j_lower + 1].setText(str(lower_cutoff))

            Fs2 = upper_cutoff + 1
            if Fs2 >= Fs/2:
                Fs2 = Fs/2-0.1
                if Fs2 <= upper_cutoff:
                    upper_cutoff = Fs2 - 0.1
                    self.graph_header_option_fields[i_upper, j_upper + 1].setText(str(upper_cutoff))

            f, H = sp.Filtering().fftbandpass(np.arange(1000), Fs, Fs1, lower_cutoff, upper_cutoff, Fs2, output='response')
            # self.FilterResponseAxis.set_xlim(0.01, 2 * Fs2)

            # self.FilterResponseAxis.plot(f, H, 'b')
            self.FilterResponseAxis.semilogx(f, H, 'b')

            self.FilterResponseAxis.axvline(upper_cutoff, color='green')
            self.FilterResponseAxis.axvline(lower_cutoff, color='green')

        self.FilterResponseAxis.set_xscale('log')
        self.FilterResponseAxis.grid(which='both', axis='both')
        self.FilterResponseAxis.set_ylim(0, 1.1)
        self.FilterResponseAxis.set_xlabel('Frequency(Hz)')
        self.FilterResponseAxis.set_ylabel('Gain [V/V]')

        self.FilterResponseCanvas.draw()

    def update_plots(self, source, x, y, kwargs):
        if source == 'Main':

            self.mainWindow.Graph_axis.plot(x, y, **kwargs)

            self.mainWindow.Graph_axis.setXRange(self.mainWindow.current_time, self.mainWindow.current_time +
                                 self.mainWindow.windowsize, padding=0)
            self.mainWindow.Graph_axis.setClipToView(True)

            if hasattr(self.mainWindow, 'graph_max'):
                self.mainWindow.Graph_axis.setYRange(0, self.mainWindow.graph_max, padding=0)

        elif source == 'MarkPeaks':
            # vlines = custom_vlines(x, y[0], y[1], style=QtCore.Qt.DashLine, **kwargs)
            vlines = custom_vlines(x, y[0], y[1], **kwargs)
            self.mainWindow.Graph_axis.addItem(vlines)

            '''
            [self.mainWindow.Graph_axis.addItem(pg.InfiniteLine(pos=peak_time, angle=90, movable=False,
                                                bounds=[0,
                                                        y],
                                                pen=(0, 0, 0))) for peak_time in x]
                                                '''
            self.mainWindow.Graph_axis.setClipToView(True)
        elif source == 'PlotSpikes':
            if 'colors' in kwargs.keys():
                pen = kwargs['colors']
            vlines = custom_vlines(x, y[0], y[1], pen=pen)
            self.mainWindow.Graph_axis.addItem(vlines)
            self.mainWindow.Graph_axis.setClipToView(True)

    def mouse_slot(self, action):
        if action == 'create':
            self.mainWindow.mouse_vLine = pg.InfiniteLine(angle=90, movable=False)
            # self.mainWindow.mouse_hLine = pg.InfiniteLine(angle=0, movable=False)
            self.mainWindow.Graph_axis.addItem(self.mainWindow.mouse_vLine, ignoreBounds=True)
            # self.mainWindow.Graph_axis.addItem(self.mainWindow.mouse_hLine, ignoreBounds=True)

            self.mainWindow.proxy = pg.SignalProxy(self.mainWindow.Graph_axis.scene().sigMouseMoved, rateLimit=100,
                                   slot=self.mainWindow.mouseMoved)

    def changeFilter(self, i, j):
        lower = False
        upper = False
        for option, position in self.graph_header_option_positions.items():
            if 'low' in option.lower():
                i_lower, j_lower = position
                lower = True
                if lower and upper:
                    break
            elif 'upper' in option.lower():
                i_upper, j_upper = position
                upper = True
                if lower and upper:
                    break

        filter_choice = self.graph_header_option_fields[i, j + 1].currentText().lower()

        if 'low' in filter_choice:
            self.graph_header_option_fields[i_lower, j_lower + 1].setDisabled(1)
            self.graph_header_option_fields[i_lower, j_lower + 1].setText('N/A')
            self.graph_header_option_fields[i_upper, j_upper + 1].setEnabled(1)
            self.graph_header_option_fields[i_upper, j_upper + 1].setText('')

        elif 'high' in filter_choice:
            self.graph_header_option_fields[i_lower, j_lower + 1].setEnabled(1)
            self.graph_header_option_fields[i_lower, j_lower + 1].setText('')
            self.graph_header_option_fields[i_upper, j_upper + 1].setDisabled(1)
            self.graph_header_option_fields[i_upper, j_upper + 1].setText('N/A')

        elif 'band' in filter_choice:
            self.graph_header_option_fields[i_lower, j_lower + 1].setEnabled(1)
            self.graph_header_option_fields[i_lower, j_lower + 1].setText('')
            self.graph_header_option_fields[i_upper, j_upper + 1].setEnabled(1)
            self.graph_header_option_fields[i_upper, j_upper + 1].setText('')

        elif 'none' in filter_choice:
            self.graph_header_option_fields[i_lower, j_lower + 1].setDisabled(1)
            self.graph_header_option_fields[i_lower, j_lower + 1].setText('N/A')
            self.graph_header_option_fields[i_upper, j_upper + 1].setDisabled(1)
            self.graph_header_option_fields[i_upper, j_upper + 1].setText('N/A')

    def changeMethod(self, i , j):
        for option, position in self.graph_header_option_positions.items():
            if 'Filter Type' in option:
                i_type, j_type = position
                break

        current_type = self.graph_header_option_fields[i, j + 1].currentText()
        if 'fft' in current_type:
            # this can only be a bandpass filter
            self.graph_header_option_fields[i_type, j_type + 1].setCurrentIndex(
                self.graph_header_option_fields[i_type, j_type + 1].findText('Bandpass'))

            # disable filter type options
            self.graph_header_option_fields[i_type, j_type + 1].setDisabled(1)
        else:
            # enable filter type options
            self.graph_header_option_fields[i_type, j_type + 1].setEnabled(1)

    def validateSource(self, action):

        # check that the Source is valid
        for option_value, (i, j) in self.graph_header_option_positions.items():
            if 'Source' in option_value:
                if 'Combo' in str(self.graph_header_option_fields[i, j + 1]):
                    value = self.graph_header_option_fields[i, j + 1].currentText()
                else:
                    value = self.graph_header_option_fields[i, j + 1].text()
                try:
                    session_path, set_filename = os.path.split(self.mainWindow.current_set_filename)
                except AttributeError:
                    '''the current_set_filename attribute doesnt exist yet, thus none was set'''
                    self.mainWindow.ErrorDialogue.myGUI_signal.emit("ImportSetError")
                    return

                session = os.path.splitext(set_filename)[0]
                if 'Speed' not in value:
                    source_filename = os.path.join(session_path, '%s%s' % (session, value))
                else:
                    source_filename = os.path.join(session_path, '%s.pos' % session)

                if 'Import a .Set' in value:
                    '''emit no .set chosen'''
                    self.mainWindow.ErrorDialogue.myGUI_signal.emit("ImportSetError")
                    return
                elif not os.path.exists(source_filename):
                    self.mainWindow.ErrorDialogue.myGUI_signal.emit("InvalidSourceFname")
                    return
                break

        # check that the user has correct filter options
        for option in self.graph_header_options:
            if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                continue
            for option_value, (i, j) in self.graph_header_option_positions.items():
                if option == option_value and 'Cutoff' in option:
                    try:
                        value = float(self.graph_header_option_fields[i, j + 1].text())
                    except ValueError:
                        # couldn't convert to a float emit invalid cutoff error or the value N/A
                        value = self.graph_header_option_fields[i, j + 1].text()
                        if 'N/A' not in value:
                            self.mainWindow.choice = ''
                            self.mainWindow.ErrorDialogue.myGUI_signal.emit("InvalidCutoff")
                            while self.mainWindow.choice == '':
                                time.sleep(0.1)
                            return
                        else:
                            # don't need to subject to further validation since the cutoff is N/A
                            break

                    if value < 0:
                        self.mainWindow.choice = ''
                        self.mainWindow.ErrorDialogue.myGUI_signal.emit("NegativeCutoff")
                        while self.mainWindow.choice == '':
                            time.sleep(0.1)
                        return
                    if 'egf' not in source_filename:
                        if value > 125:
                            self.mainWindow.choice = ''
                            self.mainWindow.ErrorDialogue.myGUI_signal.emit("EGFNecessary")
                            while self.mainWindow.choice == '':
                                time.sleep(0.1)
                            return
                    else:
                        if value > 2400:
                            self.mainWindow.choice = ''
                            self.mainWindow.ErrorDialogue.myGUI_signal.emit("InvalidEGFCutoff")
                            while self.mainWindow.choice == '':
                                time.sleep(0.1)
                            return

        if 'add' in action:
            self.addSource()
        elif 'update' in action:
            self.updateSource()

    def addSource(self):
        option_index = 0
        new_item = QtGui.QTreeWidgetItem()

        # find source
        for option in self.graph_header_options:
            if option != 'Source:':
                continue
            for option_value, (i, j) in self.graph_header_option_positions.items():
                if option == option_value:
                    source = self.graph_header_option_fields[i, j + 1].currentText()
                    break

        for option in self.graph_header_options:
            if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                continue
            for option_value, (i, j) in self.graph_header_option_positions.items():
                if option == option_value:

                    if 'Speed' not in source:

                        if 'Arena:' not in option:
                            if 'Combo' in str(self.graph_header_option_fields[i, j + 1]):
                                # then the object is a combobox
                                value = self.graph_header_option_fields[i, j + 1].currentText()

                                # new_item.setText(option_index, value)
                            elif 'LineEdit' in str(self.graph_header_option_fields[i, j + 1]):
                                # the object is a QTextEdit
                                value = self.graph_header_option_fields[i, j + 1].text()
                                # new_item.setText(option_index, value)
                            elif 'CheckBox' in str(self.graph_header_option_fields[i, j + 1]):
                                # the object is a checkbox
                                checked = self.graph_header_option_fields[i, j + 1].isChecked()
                                if checked:
                                    value = 'Yes'
                                else:
                                    value = 'No'
                        else:
                            value = 'N/A'
                    else:
                        speed_parameters = ['Source:', 'Arena:', 'Gain (V/V):', 'Hilbert']
                        if any(option in x for x in speed_parameters):
                            if 'Combo' in str(self.graph_header_option_fields[i, j + 1]):
                                # then the object is a combobox
                                value = self.graph_header_option_fields[i, j + 1].currentText()

                                # new_item.setText(option_index, value)
                            elif 'LineEdit' in str(self.graph_header_option_fields[i, j + 1]):
                                # the object is a QTextEdit
                                value = self.graph_header_option_fields[i, j + 1].text()
                                # new_item.setText(option_index, value)
                            elif 'CheckBox' in str(self.graph_header_option_fields[i, j + 1]):
                                # the object is a checkbox
                                checked = self.graph_header_option_fields[i, j + 1].isChecked()
                                if checked:
                                    value = 'Yes'
                                else:
                                    value = 'No'

                        else:
                            value = 'N/A'

                    new_item.setText(option_index, value)
                    option_index += 1
                    break

        self.graphs.addTopLevelItem(new_item)

        self.setDefaultOptions()

        self.ActiveSourceSignal.myGUI_signal.emit('update')

        self.mainWindow.plot_thread = QtCore.QThread()
        self.mainWindow.plot_thread.start()
        self.mainWindow.plot_thread_worker = Worker(self.Plot)
        self.mainWindow.plot_thread_worker.moveToThread(self.mainWindow.plot_thread)
        self.mainWindow.plot_thread_worker.start.emit("start")
        # self.Plot() # plot the new added graph

    def sourceSelected(self):
        root = self.graphs.invisibleRootItem()
        for item in self.graphs.selectedItems():
            option_index = 0
            for option in self.graph_header_options:
                if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                    continue
                for option_value, (i, j) in self.graph_header_option_positions.items():
                    if option == option_value:
                        value = item.data(option_index, 0)
                        if 'Combo' in str(self.graph_header_option_fields[i, j + 1]):
                            if value != 'N/A':
                                index = self.graph_header_option_fields[i, j + 1].findText(value)
                                self.graph_header_option_fields[i, j + 1].setCurrentIndex(index)
                            else:
                                self.graph_header_option_fields[i, j + 1].setCurrentIndex(0)

                        elif 'LineEdit' in str(self.graph_header_option_fields[i, j + 1]):
                            self.graph_header_option_fields[i, j + 1].setText(value)
                        elif 'CheckBox' in str(self.graph_header_option_fields[i, j + 1]):
                            if 'yes' in value.lower():
                                if self.graph_header_option_fields[i, j + 1].isChecked():
                                    pass
                                else:
                                    self.graph_header_option_fields[i, j + 1].toggle()
                            elif 'no' in value.lower():
                                if self.graph_header_option_fields[i, j + 1].isChecked():
                                    self.graph_header_option_fields[i, j + 1].toggle()
                                else:
                                    pass

                        option_index += 1

    def Plot(self):

        self.progress_signal.start_signal.emit('start')

        while not hasattr(self, 'progdialog'):
            time.sleep(0.1)

        graph_axis = self.mainWindow.Graph_axis

        # time.sleep(0.1)

        while self.plotting:
            time.sleep(0.1)

        self.plotting = True
        # clear the current graph
        graph_axis.clear()

        self.newData.mouse_signal.emit('create')  # emits signal to create moving vertical line with the mouse

        self.newData.lr_signal.emit('create')  # this will create the linear region selector since we cleared it above
        # self.mainWindow.create_lr()  # this will create the linear region selector since we cleared it above

        self.mark_source = []
        self.source_values = []
        self.hilbert_sources = []
        self.gain_sources = []

        if not hasattr(self.mainWindow, 'current_set_filename'):
            return

        session_path, set_filename = os.path.split(self.mainWindow.current_set_filename)
        session = os.path.splitext(set_filename)[0]

        # print(self.graphs.topLevelItemCount())

        iterator = QtGui.QTreeWidgetItemIterator(self.graphs)

        # define the location in the QTreeWidget where our variables are located
        option_index = 0
        option_tree_locations = {}

        for option in self.graph_header_options:
            if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                continue
            option_tree_locations[option] = option_index
            option_index += 1

        # iterate through each graph added
        self.progress_signal.mysignal.emit('setText', {'text': 'Collecting Source Information'})
        # self.progdialog.setLabelText('Collecting Source Information')
        while iterator.value():
            graph_item = iterator.value()  # define the current graph + data within the graph item

            # define each of the variables of the graph
            for option, option_index in option_tree_locations.items():
                # print(option)
                if 'Source' in option:
                    graph_source = graph_item.data(option_index, 0)

                    if 'Speed' not in graph_source:
                        source_filename = os.path.join(session_path, '%s%s' % (session, graph_source))
                    else:
                        source_filename = os.path.join(session_path, '%s.pos' % (session))

                elif 'Filter Method' in option:
                    filter_method = graph_item.data(option_index, 0)

                elif 'Filter Order' in option:
                    try:
                        order = int(graph_item.data(option_index, 0))
                    except ValueError:
                        pass

                elif 'Filter Type' in option:
                    filter_type = graph_item.data(option_index, 0)

                elif 'Arena' in option:
                    arena = graph_item.data(option_index, 0)

                elif 'Lower' in option:
                    lower_cutoff = graph_item.data(option_index, 0)

                elif 'Upper' in option:
                    upper_cutoff = graph_item.data(option_index, 0)

                elif 'Notch' in option:
                    notch_filter = graph_item.data(option_index, 0)
                elif 'Mark' in option:
                    mark_peaks = graph_item.data(option_index, 0)
                    if 'yes' in mark_peaks.lower():
                        mark_peaks = True
                    else:
                        mark_peaks = False
                    self.mark_source.append(mark_peaks)

                elif 'Hilbert' in option:
                    hilbert_value = graph_item.data(option_index, 0)
                    if hilbert_value == '':
                        hilbert_value = 'No'
                    elif hilbert is None:
                        hilbert_value = 'No'

                    if 'yes' in hilbert_value.lower():
                        hilbert_value = True
                    else:
                        hilbert_value = False
                    self.hilbert_sources.append(hilbert_value)

                elif 'Gain' in option:
                    gain = graph_item.data(option_index, 0)
                    if gain == '':
                        gain = 1

                    if gain != 'N/A':
                        self.gain_sources.append(float(gain))

            if not os.path.exists(source_filename):
                self.mainWindow.choice = ''
                self.mainWindow.ErrorDialogue.myGUI_signal.emit('InvalidSourceFname')
                while self.mainWindow.choice == '':
                    time.sleep(0.1)
                return

            if self.mainWindow.source_duration is None:
                self.mainWindow.source_duration = np.float(get_setfile_parameter('duration',
                                                                                 self.mainWindow.current_set_filename))

            if '.eeg' in source_filename or '.egf' in source_filename:
                if source_filename not in self.loaded_sources.keys():
                    EEG, Fs = ReadEEG(source_filename)
                    try:
                        EEGRaw, _ = bits2uV(EEG, source_filename)  # converting the EEG from bits to uV
                    except TintException:
                        # this means there was no set file
                        self.mainWindow.choice = ''
                        self.mainWindow.ErrorDialogue.myGUI_signal.emit('NoSetBits2uV')
                        while self.mainWindow.choice == '':
                            time.sleep(0.1)

                        if self.mainWindow.choice == QtGui.QMessageBox.Abort:
                            return
                        else:  # Try to find the .set File

                            search_directory = os.path.dirname(os.path.dirname(self.mainWindow.current_set_filename))
                            set_filepath = findfile(set_filename, search_directory, directory_search_max=3)

                            if set_filepath == '':
                                self.mainWindow.choice = ''
                                self.mainWindow.ErrorDialogue.myGUI_signal.emit("NoAutoSet")
                                while self.mainWindow.choice == '':
                                    time.sleep(0.1)

                                if self.mainWindow.choice == QtGui.QMessageBox.Ok:
                                    return

                            else:
                                EEGRaw, _ = bits2uV(EEG, source_filename,
                                                    set_fpath=set_filepath)  # converting the EEG from bits to uV

                    EEG = None  # don't need this variable anymore

                    # Interpolating the EEG to increase the array length by a factor of 10

                    # EEG_times_original = 1000 * np.linspace(0, len(EEGRaw) / Fs, num=len(EEGRaw), endpoint=False)  # The original EEG times (ms)
                    # Fs_interp = Fs * 10  # the new sampling rate due to the interpolation
                    # EEG_times = 1000 * np.linspace(0, len(EEGRaw) / Fs, num=10 * len(EEGRaw), endpoint=False)  # the interpolated EEG times

                    # EEGRaw = np.interp(EEG_times, EEG_times_original, EEGRaw)  # the new interpolated EEG values

                    # self.loaded_sources[source_filename] = [EEGRaw.copy(), Fs_interp]
                    self.loaded_sources[source_filename] = [EEGRaw, Fs]
                    EEG_times = None
                    EEGRaw = None

                EEGRaw = self.loaded_sources[source_filename][0]
                Fs = self.loaded_sources[source_filename][1]
                # ------- filter the EEG data for the ----------------

                if 'fft' not in filter_method:
                    if 'none' not in filter_type.lower():

                        if 'low pass' in filter_type.lower():
                            upper_cutoff = float(upper_cutoff)
                            EEG = sp.Filtering().iirfilt(bandtype='low', data=EEGRaw, Fs=Fs, Wp=upper_cutoff, order=order,
                                                         automatic=0, Rp=0.1, As=60, filttype=filter_method, showresponse=0)

                        elif 'high pass' in filter_type.lower():
                            lower_cutoff = float(lower_cutoff)
                            EEG = sp.Filtering().iirfilt(bandtype='high', data=EEGRaw, Fs=Fs, Wp=lower_cutoff, order=order,
                                                         automatic=0, Rp=0.1, As=60, filttype='butter', showresponse=0)

                        elif 'bandpass' in filter_type.lower():
                            lower_cutoff = float(lower_cutoff)
                            upper_cutoff = float(upper_cutoff)
                            EEG = sp.Filtering().iirfilt(bandtype='band', data=EEGRaw, Fs=Fs, Wp=lower_cutoff, Ws=upper_cutoff,
                                                         order=order, automatic=0, Rp=0.1, As=60, filttype='butter',
                                                         showresponse=0)
                    else:
                        # then there is no filter, so leave the raw data
                        EEG = EEGRaw.copy()

                else:
                    lower_cutoff = float(lower_cutoff)
                    upper_cutoff = float(upper_cutoff)

                    Fs1 = lower_cutoff - 1
                    if Fs1 <= 0:
                        Fs1 = 0.1

                        if Fs1 >= lower_cutoff:
                            lower_cutoff = Fs1 + 0.1

                    Fs2 = upper_cutoff + 1
                    if Fs2 >= Fs / 2:
                        Fs2 = Fs / 2 - 0.1
                        if Fs2 <= upper_cutoff:
                            upper_cutoff = Fs2 - 0.1

                    EEG = sp.Filtering().fftbandpass(EEGRaw, Fs, Fs1, lower_cutoff, upper_cutoff, Fs2)


                EEGRaw = None

                if 'none' not in notch_filter.lower():
                    '''notch filter at whichever frequency the user chose'''
                    notch_filter_frequency = int(notch_filter[:notch_filter.find(' Hz')])
                    EEG = sp.Filtering().notch_filt(EEG, Fs, freq=notch_filter_frequency, band=10,
                                              order=3)
                else:
                    '''Don't notch filter the data'''
                    pass

                self.source_values.append([EEG, Fs])

            elif '.pos' in source_filename:
                if source_filename not in self.loaded_sources.keys():
                    posx, posy, post = getpos(source_filename, arena)

                    # centering the positions
                    center = centerBox(posx, posy)
                    posx = posx - center[0]
                    posy = posy - center[1]

                    # Threshold for how far a mouse can move (100cm/s), in one sample (sampFreq = 50 Hz
                    threshold = 100 / 50  # defining the threshold

                    posx, posy, post = remBadTrack(posx, posy, post,
                                                   threshold)  # removing bad tracks (faster than threshold)


                    # nonNanValues = [index[0] for index in enumerate(posx) if np.isnan(posx[index[0]]) == False]
                    # nonNanValues = np.where(np.isnan(posx) is False)[0]
                    nonNanValues = np.where(np.isnan(posx) == False)[0]
                    # removing any NaNs
                    post = post[nonNanValues]
                    posx = posx[nonNanValues]
                    posy = posy[nonNanValues]

                    """
                    # try smoothing the positions before taking the speed
                    for index in range(7, len(posx) - 7):
                        if index == len(posx) - 8:
                            posx[index] = np.nanmean(posx[index - 7:])
                            posy[index] = np.nanmean(posy[index - 7:])
                        else:
                            posx[index] = np.nanmean(posx[index - 7:index + 7 + 1])
                            posy[index] = np.nanmean(posy[index - 7:index + 7 + 1])
                    """

                    # posx = signal.savgol_filter(posx.flatten(), 15, 4).reshape((-1, 1))
                    # posy = signal.savgol_filter(posy.flatten(), 15, 4).reshape((-1, 1))

                    # box car smoothing, closest we could get to replicating Tint's speeds
                    B = np.ones((int(np.ceil(0.4 * 50)), 1)) / np.ceil(0.4 * 50)
                    posx = scipy.ndimage.correlate(posx, B, mode='nearest')
                    posy = scipy.ndimage.correlate(posy, B, mode='nearest')

                    speed = speed2D(posx, posy, post)
                    self.loaded_sources[source_filename] = [speed, 50]  # the raw data

                    speed = None
                    posx = None
                    posy = None
                    post = None

                speed = self.loaded_sources[source_filename][0]
                Fs = self.loaded_sources[source_filename][1]

                self.source_values.append([speed, Fs])  # the filtered data

            self.progress_value += 25/self.graphs.topLevelItemCount()
            self.progress_signal.mysignal.emit('setValue', {'value': self.progress_value})
            # self.progdialog.setValue(self.progress_value)
            iterator += 1

        # self.rectangle_selector()
        # self.rectangle_selector = pg.LinearRegionItem([400, 700])

        # ------------------ the rectangle selection option END-----------------------------------------

        # find the difference in amplitudes
        graph_y_range = 0
        for source in self.source_values:
            graph_y_range += (np.amax(source[0]) - np.amin(source[0]))

        previous_source_max = 0
        # plot the spikes

        self.progress_signal.mysignal.emit('setText', {'text': 'Plotting Spikes (if checked).'})
        # self.progdialog.setLabelText('Plotting Spikes (if checked).')

        if self.mainWindow.plot_spikes:

            if len(self.mainWindow.active_tetrodes) > 0:
                if self.cell_spike_time_array == []:
                    self.spike_colors = ['k', 'b', 'g', 'r', 'c', 'm', 'y', ]
                    self.spike_colors_index = 0
                    self.spike_color_list = []
                    # ------- getting the spike data -------------------
                    for tetrode_number in self.mainWindow.active_tetrodes:

                        tetrode_file = os.path.join(session_path, '%s.%d' % (session, tetrode_number))

                        if not os.path.exists(tetrode_file):
                            pass

                        cut_file = os.path.join(tetrode_file, ''.join(
                            [os.path.splitext(os.path.basename(tetrode_file))[0], '_', str(tetrode_number), '.cut']))

                        if not os.path.exists(cut_file):
                            pass

                        units, available_units = find_unit(os.path.dirname(tetrode_file), [tetrode_file])
                        available_units = available_units[0]
                        spike_times, _, _, _, _, _ = getspikes(tetrode_file)

                        # check if the user separated bad cells from good cells
                        plottable_units = find_consec(available_units)[0]

                        for cell_num in plottable_units:
                            if cell_num == 0:
                                continue

                            self.cell_labels.append(cell_num)
                            cell_spike_times = 1000 * spike_times[np.where((units == cell_num))[1]]
                            self.cell_spike_time_array.append(cell_spike_times)
                            self.spike_color_list.append(self.spike_colors[self.spike_colors_index])
                        self.spike_colors_index += 1

                raster_spike_height = (0.30 / len(self.cell_spike_time_array)) * graph_y_range
                current_cell_raster_minimum = 0  # start at 0 amplitude
                for i in range(len(self.cell_spike_time_array)):
                    cell_spike_times = self.cell_spike_time_array[i]
                    '''
                    graph_axis.vlines(cell_spike_times, current_cell_raster_minimum,
                                      current_cell_raster_minimum + raster_spike_height,
                                      lw=2, colors=self.spike_color_list[i])
                                      
                    [graph_axis.addItem(pg.InfiniteLine(pos=spike_time, angle=90, movable=False,
                                             bounds=[current_cell_raster_minimum,
                                                     current_cell_raster_minimum + raster_spike_height],
                                             pen=(0, 0, 0))) for spike_time in cell_spike_times]
                    '''
                    # plots the vertical lines, the InfiniteLine does not plot an array like vlines, so we need to do
                    # a for loop, this method could be significantly slower
                    self.newData.mysignal.emit('PlotSpikes', cell_spike_times, np.array(
                        [current_cell_raster_minimum, current_cell_raster_minimum + raster_spike_height]),
                                               {'colors': self.spike_color_list[i]})

                    current_cell_raster_minimum += raster_spike_height  # increment the minumum height

                previous_source_max = current_cell_raster_minimum + raster_spike_height

        self.progress_value += 25
        self.progress_signal.mysignal.emit('setValue', {'value': self.progress_value})
        # self.progdialog.setValue(self.progress_value)

        self.progress_signal.mysignal.emit('setText', {'text': 'Plotting Sources.'})
        # self.progdialog.setLabelText('Plotting Sources.')
        # plotting the data
        self.source_lengths = []
        for i, source in enumerate(self.source_values):
            data = np.multiply(source[0], self.gain_sources[i])
            self.source_lengths.append(len(data))
            Fs = source[1]
            data_times = 1000 * np.linspace(0, len(data) / Fs, num=len(data), endpoint=False)
            shift_amount = - np.nanmin(data) + previous_source_max  # calculating shift

            envelope = None
            if self.hilbert_sources[i]:
                # plot the hilbert transformation
                # for the hilbert to work you need to shift the data signal after calculating the envelope
                analytic_signal = hilbert(data)
                envelope = np.abs(analytic_signal)
                envelope += shift_amount
                # graph_axis.plot(data_times, envelope, 'r')
                self.newData.mysignal.emit('Main', data_times, envelope, {'pen': (255, 0, 0)})
                # graph_axis.plot(data_times, envelope, pen=(255, 0, 0))  # plots the hilbert transform in red

            data += shift_amount  # shifts the data so it is plotted above the previous one
            previous_source_max = np.nanmax(data)  # sets the new max value for the next plot
            if envelope is not None:
                if np.amax(envelope) > previous_source_max:
                    previous_source_max = np.amax(envelope)

            # graph_axis.plot(data_times, data, 'b')  # plots the data
            self.newData.mysignal.emit('Main', data_times, data, {'pen': (0, 0, 255)})
            # graph_axis.plot(data_times, data, pen=(0, 0, 255))  # plots the source data in blue

            self.progress_value += 25 / len(self.source_values)
            self.progress_signal.mysignal.emit('setValue', {'value': self.progress_value})
            # self.progdialog.setValue(self.progress_value)

        self.mainWindow.graph_max = previous_source_max

        self.progress_signal.mysignal.emit('setText', {'text': 'Mark Peaks (if checked).'})
        # self.progdialog.setLabelText('Mark Peaks (if checked).')
        # if the user chose to mark peaks, mark each of the peaks
        for i in range(len(self.source_values)):
            if self.mark_source[i]:
                source = self.source_values[i]
                data = source[0]
                Fs = source[1]
                data_times = 1000 * np.linspace(0, len(data) / Fs, num=len(data), endpoint=False)
                peak_indices = detect_peaks(data, mpd=1, threshold=0)
                peak_times = data_times[peak_indices]
                '''
                graph_axis.vlines(peak_times, 0,
                                  previous_source_max,
                                  lw=1, linestyles='dashed')
                                  
                [graph_axis.addItem(pg.InfiniteLine(pos=peak_time, angle=90, movable=False,
                                                    bounds=[0,
                                                            previous_source_max],
                                                    pen=(0, 0, 0))) for peak_time in peak_times]
                '''

                self.newData.mysignal.emit('MarkPeaks', peak_times,
                                           np.array([0, previous_source_max]), {'pen': (0, 0, 0),
                                                                                'style': QtCore.Qt.DashLine,
                                                                               'width': 1})

                # self.newData.mysignal.emit('MarkPeaks', peak_times, previous_source_max, {})
            self.progress_value += 25 / len(self.source_values)
            self.progress_signal.mysignal.emit('setValue', {'value': self.progress_value})
            # self.progdialog.setValue(self.progress_value)


        try:
            self.mainWindow.SourceLength = np.amax(self.source_lengths)
            self.source_index = np.where(self.source_lengths == self.mainWindow.SourceLength)[0][0]
        except UnboundLocalError:
            self.plotting = False
            # self.mainWindow.GraphCanvas.draw()
            return
        except ValueError:
            self.plotting = False
            # self.mainWindow.GraphCanvas.draw()
            return

        Fs = self.source_values[self.source_index][1]
        self.mainWindow.SourceFs = Fs
        self.mainWindow.GraphLoaded = True

        # --- set the mins and maxs of the scrollbar -----
        self.mainWindow.scrollbar.setMinimum(0)
        self.mainWindow.scrollbar.setMaximum(len(data) - (self.mainWindow.windowsize / 1000 * Fs))
        self.mainWindow.scrollbar.setPageStep(2000)
        self.mainWindow.scrollbar.setSingleStep(1000)

        '''
        graph_axis.axis([self.mainWindow.current_time, self.mainWindow.current_time +
                         self.mainWindow.windowsize, 0, self.mainWindow.graph_max])
        '''

        '''
        try:
            self.mainWindow.GraphCanvas.draw()
        except IndexError:
            pass
        '''
        self.plotting = False
        # update the iterator to continue with the next graph

        self.progress_signal.mysignal.emit('setValue', {'value': 100})
        # self.progdialog.setValue(100)

        self.progress_signal.close_signal.emit('emit')
        # self.progdialog.close()

    def PlotSlice(self):
        pass

    def setDefaultOptions(self):

        for option, (i, j) in self.graph_header_option_positions.items():
            if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                continue

            if 'Combo' in str(self.graph_header_option_fields[i, j + 1]):

                if 'Notch' in option:
                    index_value = self.graph_header_option_fields[i, j + 1].findText('60 Hz')
                    self.graph_header_option_fields[i, j + 1].setCurrentIndex(index_value)
                else:
                    self.graph_header_option_fields[i, j + 1].setCurrentIndex(0)

            elif 'LineEdit' in str(self.graph_header_option_fields[i, j + 1]):
                if 'Gain' in option:
                    self.graph_header_option_fields[i, j + 1].setText('1')

            elif 'CheckBox' in str(self.graph_header_option_fields[i, j + 1]):
                if 'Hilbert' in option:
                    if self.graph_header_option_fields[i, j + 1].isChecked():
                        self.graph_header_option_fields[i, j + 1].toggle()

            self.graphs.clearSelection()

    def removeSource(self):
        root = self.graphs.invisibleRootItem()
        for item in self.graphs.selectedItems():
            (item.parent() or root).removeChild(item)

        self.ActiveSourceSignal.myGUI_signal.emit('update')

        self.mainWindow.plot_thread = QtCore.QThread()
        self.mainWindow.plot_thread.start()
        self.mainWindow.plot_thread_worker = Worker(self.Plot)
        self.mainWindow.plot_thread_worker.moveToThread(self.mainWindow.plot_thread)
        self.mainWindow.plot_thread_worker.start.emit("start")

    def updateSource(self):

        root = self.graphs.invisibleRootItem()

        for item in self.graphs.selectedItems():

            # find source
            for option in self.graph_header_options:
                if option != 'Source:':
                    continue
                for option_value, (i, j) in self.graph_header_option_positions.items():
                    if option == option_value:
                        source = self.graph_header_option_fields[i, j + 1].currentText()
                        break

            option_index = 0

            for option in self.graph_header_options:
                if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                    continue
                for option_value, (i, j) in self.graph_header_option_positions.items():
                    if option == option_value:

                        if 'Speed' not in source:

                            if 'Arena:' not in option:
                                if 'Combo' in str(self.graph_header_option_fields[i, j + 1]):
                                    # then the object is a combobox
                                    value = self.graph_header_option_fields[i, j + 1].currentText()

                                    # new_item.setText(option_index, value)
                                elif 'LineEdit' in str(self.graph_header_option_fields[i, j + 1]):
                                    # the object is a QTextEdit
                                    value = self.graph_header_option_fields[i, j + 1].text()
                                    # new_item.setText(option_index, value)
                                elif 'CheckBox' in str(self.graph_header_option_fields[i, j + 1]):
                                    # the object is a checkbox
                                    checked = self.graph_header_option_fields[i, j + 1].isChecked()
                                    if checked:
                                        value = 'Yes'
                                    else:
                                        value = 'No'
                            else:
                                value = 'N/A'
                        else:
                            speed_parameters = ['Source:', 'Arena:', 'Gain (V/V):', 'Hilbert']
                            if any(option in x for x in speed_parameters):
                                if 'Combo' in str(self.graph_header_option_fields[i, j + 1]):
                                    # then the object is a combobox
                                    value = self.graph_header_option_fields[i, j + 1].currentText()

                                    # new_item.setText(option_index, value)
                                elif 'LineEdit' in str(self.graph_header_option_fields[i, j + 1]):
                                    # the object is a QTextEdit
                                    value = self.graph_header_option_fields[i, j + 1].text()
                                    # new_item.setText(option_index, value)
                                elif 'CheckBox' in str(self.graph_header_option_fields[i, j + 1]):
                                    # the object is a checkbox
                                    checked = self.graph_header_option_fields[i, j + 1].isChecked()
                                    if checked:
                                        value = 'Yes'
                                    else:
                                        value = 'No'

                            else:
                                value = 'N/A'

                        item.setText(option_index, value)
                        option_index += 1
                        break

        self.ActiveSourceSignal.myGUI_signal.emit('update')

        self.setDefaultOptions()

        self.mainWindow.plot_thread = QtCore.QThread()
        self.mainWindow.plot_thread.start()
        self.mainWindow.plot_thread_worker = Worker(self.Plot)
        self.mainWindow.plot_thread_worker.moveToThread(self.mainWindow.plot_thread)
        self.mainWindow.plot_thread_worker.start.emit("start")

    def getSources(self):
        # root = self.graphs.invisibleRootItem()
        sources = []
        for item_count in range(self.graphs.topLevelItemCount()):
            source_parameters = {}
            item = self.graphs.topLevelItem(item_count)
            option_index = 0

            for option in self.graph_header_options:
                if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                    continue

                value = item.data(option_index, 0)
                source_parameters[option] = value
                option_index += 1

            sources.append(source_parameters)

        return sources

    def saveProfile(self):

        # If there are any sources, produce a file dialog
        sources = []
        iterator = QtGui.QTreeWidgetItemIterator(self.graphs)
        while iterator.value():
            sources.append(iterator.value())
            iterator += 1
        if len(sources) > 0:
            current_profile = ProfileNameDialog.returnFilename()
        else:
            return

        # get the source values
        sources = self.getSources()

        # load all profiles
        try:
            with open(self.profile_filename, 'r+') as f:
                profiles = json.load(f)
        except FileNotFoundError:
            profiles = {}

        # add the current profile data to the list of profile data
        profiles[current_profile] = sources

        # save the new profile data
        with open(self.profile_filename, 'w') as f:
            json.dump(profiles, f)

        # append the QComboBox
        for option, (i, j) in self.graph_header_option_positions.items():
            if 'Load Data' in option:
                break

        self.graph_header_option_fields[i, j+1].addItem(current_profile)

    def changeProfile(self):
        """This method is run when the load profile button is pressed"""
        for option, (i, j) in self.graph_header_option_positions.items():
            if 'Load Data' in option:
                break

        new_profile = self.graph_header_option_fields[i, j+1].currentText()
        if new_profile == self.current_profile:
            return
        else:

            self.graphs.clear()

            if new_profile == 'None':
                self.mainWindow.Graph_axis.clear()

                self.newData.mouse_signal.emit('create')

                # self.mainWindow.vb = self.Graph_axis.vb

                # self.mainWindow.create_lr()  # this will create the linear region selector since we cleared it above
                self.newData.lr_signal.emit(
                    'create')  # this will create the linear region selector since we cleared it above

                # self.mainWindow.GraphCanvas.draw()
                self.current_profile = new_profile
                return

            with open(self.profile_filename, 'r+') as f:
                profiles = json.load(f)

            sources = profiles[new_profile]
            for source in sources:
                option_index = 0
                new_item = QtGui.QTreeWidgetItem()
                for option in self.graph_header_options:
                    if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                        continue
                    for source_option, source_value in source.items():
                        if option == source_option:
                            new_item.setText(option_index, source_value)
                            option_index += 1
                            break
                self.graphs.addTopLevelItem(new_item)

            # setting the new current profile
            self.current_profile = new_profile

            self.ActiveSourceSignal.myGUI_signal.emit('update')

            self.mainWindow.plot_thread = QtCore.QThread()
            self.mainWindow.plot_thread.start()
            self.mainWindow.plot_thread_worker = Worker(self.Plot)
            self.mainWindow.plot_thread_worker.moveToThread(self.mainWindow.plot_thread)
            self.mainWindow.plot_thread_worker.start.emit("start")

    def deleteProfile(self):
        for option, (i, j) in self.graph_header_option_positions.items():
            if 'Load Data' in option:
                break

        profile = self.current_profile
        if profile == 'None':
            return
        else:
            self.graph_header_option_fields[i, j + 1].removeItem(
                self.graph_header_option_fields[i, j + 1].currentIndex())

            with open(self.profile_filename, 'r+') as f:
                profiles = json.load(f)

            profiles.pop(self.current_profile)

            with open(self.profile_filename, 'w') as f:
                json.dump(profiles, f)

    def mousePress(self, event):

        # event = event[0]  # the event input is tupe
        if event.button() == 1:
            mousePoint = self.mainWindow.vb.mapSceneToView(event.scenePos())
            # self.keydowntime = datetime.datetime.now().timestamp()
            self.keydowntime = event.time()
            self.keydown_position = (mousePoint.x(), mousePoint.y())
            # self.keydown_position = (event.x, event.y)

            delta_datetime = datetime.datetime.now().timestamp() - self.keydowntime
            if delta_datetime <= 0.2:
                # it will create a line only if the time between button press and release is small
                if hasattr(self, 'lines'):
                    if self.selected_time is not None:
                        try:
                            # self.lines.remove()
                            # remove old lines that were created
                            self.mainWindow.Graph_axis.removeItem(self.lines)
                            self.selected_time = None
                        except:
                            pass

                            # self.mainWindow.Graph_axis.lines.pop(0)
                if not hasattr(self.mainWindow, 'graph_max'):
                    return

                if hasattr(self.mainWindow, 'lr'):
                    # remove and replace the linear region selector so it doesn't show up at the same time as this line
                    self.mainWindow.Graph_axis.removeItem(self.mainWindow.lr)  # removes the lr
                    # self.mainWindow.create_lr()  # creates the lr again
                    self.newData.lr_signal.emit(
                        'create')  # creates the lr again
                    self.mainWindow.score_x1 = None
                    self.mainWindow.score_x2 = None

                # create a black vertical line
                self.lines = pg.InfiniteLine(pos=mousePoint.x(), angle=90,
                                             movable=False, pen=(0, 0, 0))

                # add the line to the plot
                self.mainWindow.Graph_axis.addItem(self.lines)
                self.selected_time = mousePoint.x()
                # self.mainWindow.GraphCanvas.draw()
                self.RePlotTFSignal.myGUI_signal.emit('RePlot')

            else:
                # this is a long press, remove any lines that were drawn
                if hasattr(self, 'lines'):
                    if self.selected_time is not None:
                        try:
                            # self.lines.remove()
                            self.mainWindow.Graph_axis.removeItem(self.lines)
                            self.selected_time = None
                        except:
                            pass

    def getActiveSources(self):

        root = self.graphs.invisibleRootItem()
        activeSources = []
        for item_count in range(self.graphs.topLevelItemCount()):
            source_parameters = {}
            item = self.graphs.topLevelItem(item_count)
            option_index = 0

            for option in self.graph_header_options:
                if option == '' or any((x in option for x in ['Load Data Profile', 'Save'])):
                    continue

                if option == 'Source:':
                    value = item.data(option_index, 0)
                    if value not in activeSources:
                        activeSources.append(value)
                    option_index += 1
                    break
                else:
                    option_index += 1

        return activeSources


class ProfileNameDialog(QtGui.QDialog):

    def __init__(self, parent=None):
        super(ProfileNameDialog, self).__init__(parent)

        profileNameLabel = QtGui.QLabel("Profile Name:")
        self.profileNameEdit = QtGui.QLineEdit()

        self.setWindowTitle('Save Profile As:')

        profileDialogText = QtGui.QLabel('In the text field, please name the profile/n' +
                                         'that you want to save, or press Cancel.')

        buttonBox = QtGui.QDialogButtonBox(QtGui.QDialogButtonBox.Ok |
                                           QtGui.QDialogButtonBox.Cancel)

        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)

        widget_layout = QtGui.QHBoxLayout()
        widget_layout.addWidget(profileNameLabel)
        widget_layout.addWidget(self.profileNameEdit)

        btn_layout = QtGui.QHBoxLayout()
        btn_layout.addWidget(buttonBox)

        layout = QtGui.QVBoxLayout()
        layout.addWidget(profileDialogText)
        layout.addLayout(widget_layout)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def getFilename(self):
        return self.profileNameEdit.text()

    @staticmethod
    def returnFilename(parent=None):
        dialog = ProfileNameDialog(parent)
        result = dialog.exec_()
        if result == QtGui.QDialog.Accepted:
            return dialog.getFilename()
        else:
            return None


def findfile(filename, search_directory, directory_search_max=3):
    avoid_directories = ['IniFiles', 'LogFiles', 'SpikeData', 'EEGAnalysis', 'CorrelationImages',
                         'PhaseLock']
    directories_searched = 0
    searched_directories = []
    filename_fullpath = ''

    while directories_searched < directory_search_max and set_filepath == '':
        for root, _, files in os.walk(search_directory, topdown=False):

            if files == []:
                continue

            if any(avoid_directories[i] in root for i in range(len(avoid_directories))):
                continue

            if [file for file in searched_directories if file == root] != []:
                continue
            else:
                searched_directories.append(root)

            filename_match = [file for file in files if filename in file]
            if filename_match == []:
                continue
            else:
                filename_fullpath = os.path.join(root, filename)
                break

    directories_searched += 1
    search_directory = os.path.dirname(search_directory)

    return filename_fullpath


class custom_vlines(pg.GraphicsObject):

    def __init__(self, x, min_y, max_y, pen=None, **kwargs):
        pg.GraphicsObject.__init__(self)

        self.x = x
        self.min_y = min_y
        self.max_y = max_y

        self.kwargs = kwargs

        self.maxRange = [None, None]
        self.moving = False
        self.movable = False
        self.mouseHovering = False

        if pen is None:
            self.pen = (200, 200, 100)

        self.setPen(pen, **kwargs)
        self.currentPen = self.pen

    def setBounds(self, bounds):
        self.maxRange = bounds
        self.setValue(self.value())

    def setPen(self, *args, **kwargs):
        self.pen = pg.fn.mkPen(*args, **kwargs)
        if not self.mouseHovering:
            self.currentPen = self.pen
            self.update()

    def setHoverPen(self, *args, **kwargs):
        self.hoverPen = pg.fn.mkPen(*args, **kwargs)

    def boundingRect(self):
        br = self.viewRect()
        return br.normalized()

    def paint(self, p, *args):
        p.setPen(self.currentPen)
        for value in self.x:
            p.drawLine(pg.Point(value, self.min_y), pg.Point(value, self.max_y))

    def dataBounds(self, axis, frac=1.0, orthoRange=None):
        if axis == 0:
            return None   ## x axis should never be auto-scaled
        else:
            return (0, 0)


class ProgressWindow(QtGui.QWidget):

    def __init__(self):
        super(ProgressWindow, self).__init__()


