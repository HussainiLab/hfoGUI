from core.TFA_Functions import stran_psd
from scipy.signal import hilbert
from core.GUI_Utils import Worker, CustomViewBox, background
import os
import numpy as np
import core.filtering as filt
from core.GUI_Utils import center
import pyqtgraph as pg
from matplotlib import cm
from matplotlib.colors import ColorConverter
from pyqtgraph.Qt import QtGui, QtCore
from scipy import interpolate
import time


class update_plots_signal(QtCore.QObject):
    """This is a custom plot signal class so we can replot from the main thread"""
    # mysignal = QtCore.pyqtSignal(object, object, object)
    mysignal = QtCore.pyqtSignal(str, object, object)


class PltWidget(pg.PlotWidget):
    """
    Subclass of PlotWidget created so that we can have a custom viewBox with our own menu on right click
    """
    def __init__(self, window, parent=None):
        """
        Constructor of the widget
        """
        super(PltWidget, self).__init__(parent, viewBox=CustomViewBox(window, self))


class TFPlotWindow(QtGui.QWidget):
    """This class provides the window for the Time Frequency Plots (Stockwell Transform)"""

    def __init__(self, main, settings):

        """This method will populate the window with the graphs, forms, buttons, widgets, etc, etc"""
        super(TFPlotWindow, self).__init__()
        background(self)
        # width = self.deskW / 4.2
        # height = self.deskH / 1.5

        # sets plots to white background and black foreground
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')
        pg.setConfigOptions(antialias=True)

        cmap = cm.get_cmap('jet', 10000)
        lut = []
        for i in range(10000):
            r, g, b = ColorConverter().to_rgb(cmap(i))
            lut.append([r * 255, g * 255, b * 255])
        self.jet_lut = np.array(lut, dtype=np.uint8)

        self.source_filename = None
        self.mainWindow = main
        self.settingsWindow = settings

        self.setWindowTitle("hfoGUI - T-F Plots")  # sets the title of the window

        self.newData = update_plots_signal()
        self.newData.mysignal.connect(self.update_plots)

        tabs = QtGui.QTabWidget()
        tfa_tab = QtGui.QWidget()
        psd_tab = QtGui.QWidget()
        # graphs - TFA Tab

        RawGraphLabel = QtGui.QLabel("Raw Graph:")
        # self.RawGraph = plt.figure()
        # self.RawGraphCanvas = FigureCanvas(self.RawGraph)
        # self.RawGraphAxis = self.RawGraph.add_axes([0.07, 0.1, 0.90, 0.85], frameon=False)
        # self.RawGraphAxis = pg.PlotWidget()
        self.RawGraphAxis = PltWidget(self)
        self.RawGraphAxis.hideButtons()
        self.RawGraphAxis.setMouseEnabled(x=False, y=False)  # disables the mouse interactions
        RawGraphLayout = QtGui.QVBoxLayout()
        RawGraphLayout.addWidget(RawGraphLabel)
        # RawGraphLayout.addWidget(self.RawGraphCanvas)
        RawGraphLayout.addWidget(self.RawGraphAxis)

        FilteredGraphLabel = QtGui.QLabel("Filtered Graph:")
        # self.FilteredGraph = plt.figure()
        # self.FilteredGraphCanvas = FigureCanvas(self.FilteredGraph)
        # self.FilteredGraphAxis = self.FilteredGraph.add_axes([0.07, 0.1, 0.90, 0.85], frameon=False)
        # self.FilteredGraphAxis = pg.PlotWidget()
        self.FilteredGraphAxis = PltWidget(self)
        self.FilteredGraphAxis.hideButtons()
        self.FilteredGraphAxis.setMouseEnabled(x=False, y=False) # disables the mouse interactions

        FilteredGraphLayout = QtGui.QVBoxLayout()
        FilteredGraphLayout.addWidget(FilteredGraphLabel)
        # FilteredGraphLayout.addWidget(self.FilteredGraphCanvas)
        FilteredGraphLayout.addWidget(self.FilteredGraphAxis)

        STransformGraph = QtGui.QLabel("Stockwell Transform:")
        # self.STransformGraph = plt.figure()
        # self.STransformGraphCanvas = FigureCanvas(self.STransformGraph)
        # self.STransformGraphAxis = self.STransformGraph.add_axes([0.07, 0.1, 0.90, 0.85], frameon=False)

        # self.STransformGraphAxis = pg.PlotWidget()
        self.STransformGraphAxis = PltWidget(self)
        self.STransformGraphAxis.hideButtons()
        self.STransformGraphAxis.setMouseEnabled(x=False, y=False) # disables the mouse interactions
        # self.STransformGraphCanvas = matplot.MatplotlibWidget()
        # self.STransformGraphCanvas.getFigure().add_axes([0.07, 0.1, 0.90, 0.85], frameon=False)
        # self.STransformGraphAxis = self.STransformGraphCanvas.getFigure().add_axes([0.07, 0.1, 0.90, 0.85], frameon=False)
        # self.STransformGraphAxis = self.STransformGraphCanvas.getFigure().add_subplot(111)

        STransformGraphLayout = QtGui.QVBoxLayout()
        STransformGraphLayout.addWidget(STransformGraph)

        # STransformGraphLayout.addWidget(self.STransformGraphCanvas)
        STransformGraphLayout.addWidget(self.STransformGraphAxis)

        # graphs - psd tab
        '''
        PSDGraph = QtGui.QLabel("PSD(uV**2/Hz):")
        self.PSDGraph = plt.figure()
        self.PSDGraphCanvas = FigureCanvas(self.PSDGraph)
        self.PSDGraphAxis = self.PSDGraph.add_axes([0.07, 0.2, 0.90, 0.75], frameon=False)
    
        PSDGraphLayout = QtGui.QVBoxLayout()
        PSDGraphLayout.addWidget(PSDGraph)
        PSDGraphLayout.addWidget(self.PSDGraphCanvas)

        PSDLogGraph = QtGui.QLabel("PSD(10log10(uV**2/Hz)):")
        self.PSDLogGraph = plt.figure()
        self.PSDLogGraphCanvas = FigureCanvas(self.PSDLogGraph)
        self.PSDLogGraphAxis = self.PSDLogGraph.add_axes([0.07, 0.2, 0.90, 0.75], frameon=False)
        PSDLogGraphLayout = QtGui.QVBoxLayout()
        PSDLogGraphLayout.addWidget(PSDLogGraph)
        PSDLogGraphLayout.addWidget(self.PSDLogGraphCanvas)
        
        graph_layout = QtGui.QVBoxLayout()
        graph_layout.addLayout(PSDGraphLayout)
        graph_layout.addLayout(PSDLogGraphLayout)
        '''

        # self.PSDGraphAxis = pg.PlotWidget()
        self.PSDGraphAxis = PltWidget(self)
        self.PSDGraphAxis.hideButtons()
        self.PSDGraphAxis.setMouseEnabled(x=False, y=False)  # disables the mouse interactions

        # self.PSDLogGraphAxis = pg.PlotWidget()
        self.PSDLogGraphAxis = PltWidget(self)
        self.PSDLogGraphAxis.hideButtons()
        self.PSDLogGraphAxis.setMouseEnabled(x=False, y=False)  # disables the mouse interactions

        graph_layout = QtGui.QVBoxLayout()
        graph_layout.addWidget(self.PSDGraphAxis)
        graph_layout.addWidget(self.PSDLogGraphAxis)

        # Button Layout
        source_combo_label = QtGui.QLabel("Source:")

        active_sources = settings.getActiveSources()

        self.source_combo = QtGui.QComboBox()
        self.source_combo.setEditable(True)
        self.source_combo.lineEdit().setReadOnly(True)
        self.source_combo.lineEdit().setAlignment(QtCore.Qt.AlignHCenter)
        self.source_combo.currentIndexChanged.connect(self.changeSources)
        self.source_combo.setSizePolicy(QtGui.QSizePolicy(
            QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Fixed))
        self.source_combo.addItem("None")
        for item in active_sources:
            self.source_combo.addItem(item)

        source_layout = QtGui.QHBoxLayout()
        source_layout.addWidget(source_combo_label)
        source_layout.addWidget(self.source_combo)

        self.hide_btn = QtGui.QPushButton("Hide")

        self.replot_btn = QtGui.QPushButton("Re-Plot")
        self.replot_btn.clicked.connect(self.RePlot)

        button_layout = QtGui.QHBoxLayout()
        for btn in [self.replot_btn, self.hide_btn]:
            button_layout.addWidget(btn)

        filter_layout = QtGui.QHBoxLayout()

        filter_layout_label = QtGui.QLabel("<b>Filtered Signal Parameters:<b>")

        low_freq_layout = QtGui.QHBoxLayout()
        low_freq_label = QtGui.QLabel('Low Freq(Hz):')
        self.low_frequency = QtGui.QLineEdit()
        self.lower_cutoff = 0
        self.low_frequency.setText(str(self.lower_cutoff))

        self.low_frequency.setAlignment(QtCore.Qt.AlignHCenter)
        self.low_frequency.textChanged.connect(self.filterFrequencyChange)
        low_freq_layout.addWidget(low_freq_label)
        low_freq_layout.addWidget(self.low_frequency)

        high_freq_layout = QtGui.QHBoxLayout()
        high_freq_label = QtGui.QLabel('High Freq(Hz):')
        self.high_frequency = QtGui.QLineEdit()
        self.upper_cutoff = 500
        self.high_frequency.setText(str(self.upper_cutoff))
        self.high_frequency.setAlignment(QtCore.Qt.AlignHCenter)
        self.high_frequency.textChanged.connect(self.filterFrequencyChange)
        high_freq_layout.addWidget(high_freq_label)
        high_freq_layout.addWidget(self.high_frequency)

        filter_layout.addWidget(filter_layout_label)
        filter_layout.addLayout(low_freq_layout)
        filter_layout.addLayout(high_freq_layout)

        # stockwell parameters

        stockwell_layout = QtGui.QHBoxLayout()
        stockwell_layout_label = QtGui.QLabel("<b>Stockwell Parameters:<b>")

        stockwell_min_freq_label = QtGui.QLabel("Low Freq(Hz):")
        self.stockwell_min_freq = QtGui.QLineEdit()
        self.stockwell_min_freq.setAlignment(QtCore.Qt.AlignHCenter)
        self.stockwell_min_freq.setText('0')
        stockwell_min_freq_layout = QtGui.QHBoxLayout()
        stockwell_min_freq_layout.addWidget(stockwell_min_freq_label)
        stockwell_min_freq_layout.addWidget(self.stockwell_min_freq)

        stockwell_max_freq_label = QtGui.QLabel("High Freq(Hz):")
        self.stockwell_max_freq = QtGui.QLineEdit()
        self.stockwell_max_freq.setAlignment(QtCore.Qt.AlignHCenter)
        self.stockwell_max_freq.setText('500')
        stockwell_max_freq_layout = QtGui.QHBoxLayout()
        stockwell_max_freq_layout.addWidget(stockwell_max_freq_label)
        stockwell_max_freq_layout.addWidget(self.stockwell_max_freq)

        self.stockwell_window_size = QtGui.QLineEdit()
        self.stockwell_window_size.setText('250')
        self.stockwell_window_size.setAlignment(QtCore.Qt.AlignHCenter)
        stockwell_window_size_label = QtGui.QLabel("Window Size(ms):")
        stockwell_window_size_layout = QtGui.QHBoxLayout()
        stockwell_window_size_layout.addWidget(stockwell_window_size_label)
        stockwell_window_size_layout.addWidget(self.stockwell_window_size)

        stockwell_notch_filter_label = QtGui.QLabel("Notch Filter Frequency(Hz):")
        self.stockwell_notch_filter = QtGui.QComboBox()
        for item in ['None', '60', '50']:
            self.stockwell_notch_filter.addItem(item)

        # sets 60 Hz as the starting
        self.stockwell_notch_filter.setCurrentIndex(self.stockwell_notch_filter.findText("60"))
        stockwell_notch_filter_layout = QtGui.QHBoxLayout()
        stockwell_notch_filter_layout.addWidget(stockwell_notch_filter_label)
        stockwell_notch_filter_layout.addWidget(self.stockwell_notch_filter)

        stockwell_layout.addWidget(stockwell_layout_label)
        stockwell_layout.addLayout(stockwell_window_size_layout)
        stockwell_layout.addLayout(stockwell_min_freq_layout)
        stockwell_layout.addLayout(stockwell_max_freq_layout)
        stockwell_layout.addLayout(stockwell_notch_filter_layout)

        # stockwell_layout.addLayout()

        # ------------ tf settings layout -----------

        tf_settings_layout = QtGui.QVBoxLayout()
        tf_settings_layout.addLayout(source_layout)
        tf_settings_layout.addLayout(filter_layout)
        tf_settings_layout.addLayout(stockwell_layout)

        # ------------------ tfa tab layout ------------------------------

        layout_order = [tf_settings_layout, RawGraphLayout, FilteredGraphLayout, STransformGraphLayout]

        layout_tf = QtGui.QVBoxLayout()
        # layout_score.addStretch(1)
        for order in layout_order:
            if 'Layout' in order.__str__():
                layout_tf.addLayout(order)
                # layout_tf.addStretch(1)
            else:
                # layout_tf.addWidget(order, 0, QtCore.Qt.AlignCenter)
                layout_tf.addWidget(order)
                # layout_tf.addStretch(1)

        # ------------- psd tab layout------------

        layout_order = [graph_layout]

        layout_psd = QtGui.QVBoxLayout()
        # layout_score.addStretch(1)
        for order in layout_order:
            if 'Layout' in order.__str__():
                layout_psd.addLayout(order)
                # layout_tf.addStretch(1)
            else:
                # layout_tf.addWidget(order, 0, QtCore.Qt.AlignCenter)
                layout_psd.addWidget(order)
                # layout_tf.addStretch(1)

        # --------- window layout ----------

        tfa_tab.setLayout(layout_tf)
        psd_tab.setLayout(layout_psd)

        tabs.addTab(tfa_tab, 'TFA Tab')
        tabs.addTab(psd_tab, 'PSD Tab')

        window_layout = QtGui.QVBoxLayout()
        window_layout.addWidget(tabs)
        window_layout.addLayout(button_layout)

        self.setLayout(window_layout)

        center(self)

    def Plot(self):

        if not self.mainWindow.GraphLoaded:
            return

        if self.source_filename is not None:

            if self.source_filename not in self.settingsWindow.loaded_sources:
                return

            if self.raw_data == []:
                self.raw_data, self.Fs = self.settingsWindow.loaded_sources[self.source_filename]

            # filter the 60 Hz of the raw data

            notch_filter_frequency = self.stockwell_notch_filter.currentText()
            if notch_filter_frequency != 'None':
                self.raw_data = filt.notch_filt(self.raw_data, self.Fs, freq=int(notch_filter_frequency), band=10,
                                            order=3)

            if self.upper_cutoff > self.Fs/2:
                self.upper_cutoff = self.Fs/2
                self.high_frequency.setText(str(self.upper_cutoff))

            if self.lower_cutoff < 0:
                self.lower_cutoff = 0
                self.low_frequency.setText(str(self.lower_cutoff))

            # filter the data if it is not already filtered
            if self.filtered_data == []:

                if self.lower_cutoff != 0 and self.upper_cutoff != self.Fs/2:
                    self.filtered_data = filt.iirfilt(bandtype='band', data=self.raw_data, Fs=self.Fs,
                                                                Wp=self.lower_cutoff, Ws=self.upper_cutoff,
                                                 order=3, automatic=0, Rp=3, As=60, filttype='butter',
                                                 showresponse=0)
                elif self.lower_cutoff == 0:
                    self.filtered_data = filt.iirfilt(bandtype='low', data=self.raw_data, Fs=self.Fs,
                                                                Wp=self.upper_cutoff,
                                                                order=3, automatic=0, Rp=3, As=60, filttype='butter',
                                                                showresponse=0)

                elif self.upper_cutoff == self.Fs/2:
                    self.filtered_data = filt.iirfilt(bandtype='high', data=self.raw_data, Fs=self.Fs,
                                                                Wp=self.lower_cutoff,
                                                                order=3, automatic=0, Rp=3, As=60, filttype='butter',
                                                                showresponse=0)

            if not hasattr(self.settingsWindow, 'selected_time'):
                return

            if self.settingsWindow.selected_time is None:
                return

            selected_time = np.rint(self.Fs * self.settingsWindow.selected_time / 1000)  # index instead of milliseconds

            if selected_time is None:
                return

            # get the window_size
            try:
                if float(self.stockwell_window_size.text())/1000 < 1:
                    enforced_1s = True
                    windowsize_1s = 1*self.Fs  # make the minimum 1 second
                    windowsize = self.Fs * float(self.stockwell_window_size.text()) / 1000  # indices
                else:
                    enforced_1s = False
                    windowsize = self.Fs * float(self.stockwell_window_size.text())/1000  # indices

            except ValueError:
                return

            # center the plot around the selected point

            plot_window_min = np.rint(selected_time - windowsize/2)
            plot_window_max = np.rint(selected_time + windowsize/2)

            if enforced_1s:
                plot_window_min_1s = np.rint(selected_time - windowsize_1s/2)
                plot_window_max_1s = np.rint(selected_time + windowsize_1s/2)

                if plot_window_min_1s < 0:
                    plot_window_min_1s = 0
                    plot_window_max_1s = np.rint(windowsize_1s)

                elif plot_window_max_1s > len(self.raw_data) - 1:
                    plot_window_max_1s = len(self.raw_data) - 1
                    plot_window_min_1s = np.rint(plot_window_max - windowsize_1s)

                else:
                    pass

            if plot_window_min < 0:
                plot_window_min = 0
                plot_window_max = np.rint(windowsize)

            elif plot_window_max > len(self.raw_data)-1:
                plot_window_max = len(self.raw_data)-1
                plot_window_min = np.rint(plot_window_max - windowsize)

            else:
                pass

            plot_window_max = np.int(plot_window_max)
            plot_window_min = np.int(plot_window_min)

            if enforced_1s:
                plot_window_max_1s = np.int(plot_window_max_1s)
                plot_window_min_1s = np.int(plot_window_min_1s)

            t = (1000 / self.Fs) * np.arange(plot_window_min, plot_window_max + 1)  # ms

            # timeseries = self.filtered_data[plot_window_min:plot_window_max + 1]
            timeseries = self.raw_data[plot_window_min:plot_window_max + 1]
            timeseries = timeseries - np.mean(timeseries)
            t_min = np.amin(t)
            t_max = np.amax(t)

            if enforced_1s:
                timeseries_1s = self.raw_data[plot_window_min_1s:plot_window_max_1s + 1]
                timeseries_1s = timeseries_1s - np.mean(timeseries_1s)

            filtered_data = self.filtered_data[plot_window_min:plot_window_max + 1]

            analytic_signal = hilbert(filtered_data)
            envelope = np.absolute(analytic_signal)

            self.newData.mysignal.emit('Raw', t, timeseries)
            self.newData.mysignal.emit('Filtered', t, np.vstack((filtered_data, envelope)))
            '''
            self.RawGraphAxis.clear()
            self.RawGraphAxis.plot(t, timeseries, 'b')
            self.RawGraphAxis.set_xlim(t_min, t_max)
            self.RawGraphAxis.vlines(self.settingsWindow.selected_time, np.amin(timeseries)-100, np.amax(timeseries)+100, lw=2,
                                     linestyles='dashed', color='k')
            self.RawGraphAxis.set_ylabel('Amplitude(uV)')
            self.RawGraphAxis.set_xlabel('Time(ms)')
            

            self.FilteredGraphAxis.clear()
            self.FilteredGraphAxis.plot(t, filtered_data, 'b', t, envelope, 'r')
            self.FilteredGraphAxis.set_xlim(t_min, t_max)
            self.FilteredGraphAxis.vlines(self.settingsWindow.selected_time, np.amin(filtered_data)-100,
                                          np.amax(filtered_data)+100, lw=2, linestyles='dashed', color='k')
            self.FilteredGraphAxis.set_ylabel('Amplitude(uV)')
            self.FilteredGraphAxis.set_xlabel('Time(ms)')
            '''

            try:
                minfreq = int(self.stockwell_min_freq.text())
                maxfreq = int(self.stockwell_max_freq.text())
            except ValueError:
                return

            try:
                if not enforced_1s:
                    power, phase, f = stran_psd(timeseries, self.Fs, minfreq=minfreq, maxfreq=maxfreq, output_Fs=1)
                else:
                    power, phase, f = stran_psd(timeseries_1s, self.Fs, minfreq=minfreq, maxfreq=maxfreq, output_Fs=1)

                    window_diff = plot_window_max - plot_window_min
                    start = plot_window_min-plot_window_min_1s
                    stop = start + window_diff+1
                    power = power[:, start:stop]

            except MemoryError:
                self.mainWindow.choice = ''
                self.mainWindow.ErrorDialogue.myGUI_signal.emit('MemoryError')

                while self.mainWindow.choice == '':
                    time.sleep(0.1)

                return

            # power, phase, f = stran_psd_old(timeseries, 0, self.Fs/2, self.Fs, 1)

            '''
            # self.STransformGraphAxis.clear()
            self.STransformGraphAxis.imshow(power, origin='lower', aspect='auto', cmap='jet', interpolation='bilinear',
                                            extent=(t_min, t_max, np.amin(f), np.amax(f)))

            self.STransformGraphAxis.vlines(self.settingsWindow.selected_time, np.amin(f), np.amax(f), lw=2,
                                            linestyles='dashed', color='w')

            self.STransformGraphAxis.set_ylabel('Frequency(Hz)')
            self.STransformGraphAxis.set_xlabel('Time(ms)')
    
            # self.RawGraphCanvas.draw()
            # self.FilteredGraphCanvas.draw()
            self.STransformGraphCanvas.draw()
            '''
            
            self.newData.mysignal.emit('T-F', t, np.hstack((power, f.reshape((-1, 1)))))

            PSD = power[:, int(np.fix(power.shape[1] / 2))]
            PSD = np.absolute(PSD)**2  # need to square the magnitude to get power spectral density
            PSDlog10 = np.multiply(np.log10(PSD), 10)
            # PSDlog10[np.where(PSD == 0)] = 0

            self.newData.mysignal.emit('PSD', f, PSD)
            self.newData.mysignal.emit('PSDLog', f, PSDlog10)

            '''
            # self.PSDGraphAxis.clear()
            # self.PSDGraphAxis.plot(f, PSD, clear=True)
            # self.PSDGraphAxis.set_xlim(min(f), max(f))
            # self.PSDGraphAxis.set_ylabel('uV**2/Hz')
            # self.PSDGraphAxis.set_xlabel('Frequency(Hz)')

            
            # self.PSDLogGraphAxis.clear()
            # self.PSDLogGraphAxis.plot(f, PSDlog10, clear=True)
            # self.PSDLogGraphAxis.set_xlim(min(f), max(f))
            # self.PSDLogGraphAxis.set_ylabel('10log10(uV**2/Hz)')
            # self.PSDLogGraphAxis.set_xlabel('Frequency(Hz)')

            # self.PSDGraphCanvas.draw()
            # self.PSDLogGraphCanvas.draw()
            '''

    def updateActiveSources(self):
        """This method updates the source combobox depending on the sources that are within the QTreeWidget within
        the GraphSettingsWindow object"""

        active_sources = self.settingsWindow.getActiveSources()  # get the list of source names within the QTreeWidget

        # get the list of current sources that are listed in the QCombobox
        current_sources = [self.source_combo.itemText(i) for i in range(self.source_combo.count())]

        # add items that are in active_sources but not in current_sources

        add_items = []
        [add_items.append(item) for item in active_sources if item not in current_sources]

        for item in add_items:
            current_sources.append(item)
            self.source_combo.addItem(item)

        # remove items that are in current_sources that are not in active_sources

        remove_items = []
        [remove_items.append(item) for item in current_sources if item not in active_sources]

        for item in remove_items:
            self.source_combo.removeItem(self.source_combo.findText(item))

    def changeSources(self):
        """This method will populate the appropriate values in the T-F window forms and runs whenever
        the user changes sources (mainly for if it changes between .egf and .eeg value files)"""
        graph_source = self.source_combo.currentText()

        if not hasattr(self.mainWindow, 'current_set_filename'):
            return

        session_path, set_filename = os.path.split(self.mainWindow.current_set_filename)
        session = os.path.splitext(set_filename)[0]
        source_filename = os.path.join(session_path, '%s%s' % (session, graph_source))

        if not os.path.exists(source_filename):
            self.source_filename = None
            return

        else:
            self.source_filename = source_filename
            if '.egf' in source_filename:
                self.low_frequency.setText('80')
                self.high_frequency.setText('500')
                self.stockwell_max_freq.setText('500')
                self.stockwell_min_freq.setText('80')
            elif '.eeg' in source_filename:
                self.low_frequency.setText('4')
                self.high_frequency.setText('12')
                self.stockwell_max_freq.setText('125')
                self.stockwell_min_freq.setText('0')

            self.raw_data = []
            self.filtered_data = []

            self.plot_thread = QtCore.QThread()
            self.plot_thread.start()
            self.plot_thread_worker = Worker(self.Plot)
            self.plot_thread_worker.moveToThread(self.plot_thread)
            self.plot_thread_worker.start.emit("start")
            # self.Plot()

    def RePlot(self):
        """This method will start a thread which will replot the data"""
        self.replot_thread = QtCore.QThread()
        self.replot_thread.start()
        self.replot_thread_worker = Worker(plot, self)
        self.replot_thread_worker.moveToThread(self.replot_thread)
        self.replot_thread_worker.start.emit("start")

    def filterFrequencyChange(self):
        """This method will update the attribute relating to the upper and lower cutoff values"""
        try:
            self.lower_cutoff = int(self.low_frequency.text())
            self.upper_cutoff = int(self.high_frequency.text())

            self.filtered_data = []
        except ValueError:
            return

        # self.RePlot()

    def clearPlots(self):
        """This method will clear the plots and data associated with it so that when a user selects a new
        .set file, nothing remainds from the previous graph"""
        self.raw_data = []
        self.filtered_data = []

        self.FilteredGraphAxis.clear()
        self.RawGraphAxis.clear()
        self.STransformGraphAxis.clear()
        # self.RawGraphCanvas.draw()
        # self.FilteredGraphCanvas.draw()
        # self.STransformGraphCanvas.draw()

        self.PSDGraphAxis.clear()
        self.PSDLogGraphAxis.clear()
        # self.PSDGraphCanvas.draw()
        # self.PSDLogGraphCanvas.draw()

    # @QtCore.pyqtSlot(str, QtCore.QObject, QtCore.QObject)
    def update_plots(self, source, x, y):
        """A method used to update the plots, a custom signal will initiate this to avoid updating the main
        thread from an alternate thread"""

        if source == 'PSD':
            # update the PSD graph
            self.PSDGraphAxis.plot(x, y, clear=True, pen=(0, 0, 255), width=3)
            self.PSDGraphAxis.setXRange(np.amin(x), np.amax(x), padding=0)
            self.PSDGraphAxis.setLabel('left', "PSD", units='uV**2/Hz')
            self.PSDGraphAxis.setLabel('bottom', "Frequency", units='Hz')

        elif source == 'PSDLog':
            # update the 10Log10 PSD graph
            self.PSDLogGraphAxis.plot(x, y, clear=True, pen=(0, 0, 255), width=3)
            self.PSDLogGraphAxis.setXRange(np.amin(x), np.amax(x), padding=0)
            self.PSDLogGraphAxis.setLabel('left', "PSD", units='10log10(uV**2/Hz)')
            self.PSDLogGraphAxis.setLabel('bottom', "Frequency", units='Hz')

        elif source == 'Raw':
            # update the raw graph (top graph)
            self.RawGraphAxis.plot(x, y, clear=True, pen=(0, 0, 255), width=3)
            vLine = pg.InfiniteLine(pos=self.settingsWindow.selected_time, angle=90, movable=False, pen=(0, 0, 0))
            self.RawGraphAxis.addItem(vLine,  ignoreBounds=True)
            self.RawGraphAxis.setXRange(np.amin(x), np.amax(x), padding=0)
            self.RawGraphAxis.setLabel('left', "Amplitude", units='uV')
            self.RawGraphAxis.setLabel('bottom', "Time", units='ms')

        elif source == 'Filtered':
            # update the filtered graph (middle graph)
            self.FilteredGraphAxis.plot(x, y[0, :], clear=True, pen=(0, 0, 255), width=3)  # plotting filtered data
            self.FilteredGraphAxis.plot(x, y[1, :], pen=(255, 0, 0), width=3)  # plotting the hilbert transform
            vLine = pg.InfiniteLine(pos=self.settingsWindow.selected_time, angle=90, movable=False, pen=(0, 0, 0))
            self.FilteredGraphAxis.addItem(vLine, ignoreBounds=True)
            self.FilteredGraphAxis.setXRange(np.amin(x), np.amax(x), padding=0)
            self.FilteredGraphAxis.setLabel('left', "Amplitude", units='uV')
            self.FilteredGraphAxis.setLabel('bottom', "Time", units='ms')

        elif source == 'T-F':
            # update the time frequency graph (bottom graph)
            power = y[:, :-1]
            freq = y[:, -1]

            # if '.eeg' in self.source_filename:
            # interpolation will allow the graph to look less pixelated

            f = interpolate.interp2d(x, freq, power, kind='linear')
            x_new = np.linspace(x[0], x[-1], num=10e2)
            y_new = np.linspace(freq[0], freq[-1], num=10e2)
            power = f(x_new, y_new)

            # colormap = cm.get_cmap("jet")  # cm.get_cmap("CMRmap")
            # colormap._init()
            # lut = (colormap._lut * 255).view(np.ndarray)  # Convert matplotlib colormap from 0-1 to 0 -255 for Qt
            self.STransformGraphAxis.clear()
            hm = pg.ImageItem()
            hm.setImage(power.T, lut=self.jet_lut)
            # hm.setLookupTable(lut)
            self.STransformGraphAxis.addItem(hm)

            vLine = pg.InfiniteLine(pos=self.settingsWindow.selected_time, angle=90, movable=False, pen=(255, 255, 255))
            vLine.setPen(style=QtCore.Qt.DashLine)
            hm.setRect(QtCore.QRectF(np.amin(x), np.amin(freq), np.amax(x)-np.amin(x), np.amax(freq)-np.amin(freq)))

            self.STransformGraphAxis.addItem(vLine)
            self.STransformGraphAxis.setXRange(np.amin(x), np.amax(x), padding=0)
            self.STransformGraphAxis.setYRange(np.amin(freq), np.amax(freq), padding=0)
            self.STransformGraphAxis.setLabel('left', "Frequency", units='Hz')
            self.STransformGraphAxis.setLabel('bottom', "Time", units='ms')


def plot(self):
    graph_source = self.source_combo.currentText()

    if not hasattr(self.mainWindow, 'current_set_filename'):
        return

    session_path, set_filename = os.path.split(self.mainWindow.current_set_filename)
    session = os.path.splitext(set_filename)[0]
    source_filename = os.path.join(session_path, '%s%s' % (session, graph_source))

    if not os.path.exists(source_filename):
        self.source_filename = None
        return

    else:
        self.source_filename = source_filename
        self.Plot()