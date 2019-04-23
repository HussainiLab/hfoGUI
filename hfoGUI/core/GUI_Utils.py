import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
import exporters
import os
import time
import sys

project_name = 'hfoGUI'


def background(self):  # defines the background for each window
    """providing the background info for each window"""
    # Acquiring information about geometry
    project_dir = os.path.dirname(os.path.abspath("__file__"))

    if os.path.basename(project_dir) != project_name:
        project_dir = os.path.dirname(sys.argv[0])

    # defining the directory filepaths
    self.PROJECT_DIR = project_dir  # project directory

    self.IMG_DIR = os.path.join(self.PROJECT_DIR, 'img')  # image directory
    self.CORE_DIR = os.path.join(self.PROJECT_DIR, 'core')  # core directory
    self.SETTINGS_DIR = os.path.join(self.PROJECT_DIR, 'settings')  # settings directory
    if not os.path.exists(self.SETTINGS_DIR):
        os.mkdir(self.SETTINGS_DIR)

    self.setWindowIcon(QtGui.QIcon(os.path.join(self.IMG_DIR, 'GEBA_Logo.png')))  # declaring the icon image
    self.deskW, self.deskH = QtWidgets.QDesktopWidget().availableGeometry().getRect()[2:]  #gets the window resolution
    self.setGeometry(0, 0, self.deskW/2, self.deskH/1.5)  # Sets the window size, 800x460 is the size of our window

    QtWidgets.QApplication.setStyle(QtWidgets.QStyleFactory.create('Cleanlooks'))


class Worker(QtCore.QObject):
    # def __init__(self, main_window, thread):
    def __init__(self, function, *args, **kwargs):
        super(Worker, self).__init__()
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.start.connect(self.run)

    start = QtCore.pyqtSignal(str)

    @QtCore.pyqtSlot()
    def run(self):

        self.function(*self.args, **self.kwargs)


def center(self):
    """centers the window on the screen"""
    frameGm = self.frameGeometry()
    screen = QtWidgets.QApplication.desktop().screenNumber(QtWidgets.QApplication.desktop().cursor().pos())
    centerPoint = QtWidgets.QApplication.desktop().screenGeometry(screen).center()
    frameGm.moveCenter(centerPoint)
    self.move(frameGm.topLeft())


class Communicate(QtCore.QObject):
    """A custom pyqtsignal so that errors and popups can be called from the threads
    to the main window"""
    myGUI_signal = QtCore.pyqtSignal(str)


def find_consec(data):
    '''finds the consecutive numbers and outputs as a list'''
    consecutive_values = []  # a list for the output
    current_consecutive = [data[0]]

    if len(data) == 1:
        return [[data[0]]]

    for index in range(1, len(data)):

        if data[index] == data[index - 1] + 1:
            current_consecutive.append(data[index])

            if index == len(data) - 1:
                consecutive_values.append(current_consecutive)

        else:
            consecutive_values.append(current_consecutive)
            current_consecutive = [data[index]]

            if index == len(data) - 1:
                consecutive_values.append(current_consecutive)
    return consecutive_values


class CustomViewBox(pg.ViewBox):
    """
    Subclass of ViewBox
    """

    def __init__(self, window, item, parent=None):
        """
        Constructor of the CustomViewBox
        """
        super(CustomViewBox, self).__init__(parent)
        # self.plot = plot
        self.window = window
        self.item = item
        self.menu = None  # Override pyqtgraph ViewBoxMenu
        self.menu = self.getMenu()  # Create the menu

    def raiseContextMenu(self, ev):
        """
        Raise the context menu
        """
        if not self.menuEnabled():
            return
        menu = self.getMenu()
        pos  = ev.screenPos()
        menu.popup(QtCore.QPoint(pos.x(), pos.y()))

    def getMenu(self):
        """
        Create the menu
        """
        if self.menu is None:
            self.menu = QtWidgets.QMenu()
            self.save_plot = QtWidgets.QAction("Save Figure", self.menu)
            self.save_plot.triggered.connect(self.export)
            self.menu.addAction(self.save_plot)
        return self.menu

    def export(self):
        # choose filename to save as
        save_filename, filename_ext = QtWidgets.QFileDialog.getSaveFileName(QtWidgets.QWidget(), 'Save Scores', '',
                                                          'PNG (*.png);;JPG (*.jpg);;TIF (*.tif);;GIF (*.gif)')

        if save_filename == '':
            return

        # create an exporter instance, as an argument give it
        # the item you wish to export

        if 'GraphicsWindow' in str(self.item):
            # get the main plot which occurs at row=1, and column=0
            plotitem = self.item.getItem(1, 0)
            # turn off the infinite line marking where the cursor is
            self.window.mouse_vLine.hide()

            exporter = exporters.ImageExporter(plotitem)

            # set export parameters if needed
            # exporter.parameters()['width'] = 100  # (note this also affects height parameter)

            # save to file
            exporter.export(save_filename)

            self.window.mouse_vLine.show()

        elif 'PltWidget' in str(self.item):
            plotitem = self.item.getPlotItem()

            exporter = exporters.ImageExporter(plotitem)

            # set export parameters if needed
            # exporter.parameters()['width'] = 100  # (note this also affects height parameter)

            # save to file
            exporter.export(save_filename)


class PltWidget(pg.PlotWidget):
    """
    Subclass of PlotWidget
    """
    def __init__(self, parent=None):
        """
        Constructor of the widget
        """
        super(PltWidget, self).__init__(parent, viewBox=CustomViewBox())


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

    elif any(x in str(new_window) for x in ['Score',
                                            'GraphSettings',
                                            'TFPlot',
                                            'PSDPlot']):
        new_window.raise_()

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


Large_Font = ("Arial", 11)  # defines two fonts for different purposes (might not be used
Small_Font = ("Arial", 8)