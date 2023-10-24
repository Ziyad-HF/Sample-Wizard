from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QApplication, QSlider
import pyqtgraph as pg
from PyQt5.uic import loadUiType
from pandas import read_csv
import sys
from PyQt5.QtGui import QIntValidator
from PyQt5 import Qt

# from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication, QColorDialog
# from pyqtgraph.Qt import QtCore, QtGui
import numpy as np
# from random import choice
from os import path  # listdir, remove

FORM_CLASS, _ = loadUiType(path.join(path.dirname(__file__), "mainWindow.ui"))


def plot(t, y, title, graph, p='b'):
    graph.clear()
    graph.addLegend(labelTextSize='10pt')
    plotted_curve = pg.PlotCurveItem(t, y, pen=p, name=title)
    graph.addItem(plotted_curve)
    # plotted_curve.setData(t, y, pen='b', name=title)


def calculate_max_frequency(signal):
    fft = np.fft.fft(signal)
    frequency = np.fft.fftfreq(len(signal))
    magnitude = np.abs(fft)
    # max_magnitude = np.max(magnitude)
    max_frequency_index = np.argmax(magnitude)
    max_frequency = np.abs(frequency[max_frequency_index])
    return round(max_frequency * 10**6)


class MainApp(QMainWindow, FORM_CLASS):

    def __init__(self, parent=None):
        super(MainApp, self).__init__(parent)
        QMainWindow.__init__(self, parent=None)
        self.setupUi(self)
        self.setWindowTitle("Sample Wizard")
        self.samplingGraph.setBackground('w')
        self.mixerGraph.setBackground('w')
        self.diffGraph.setBackground('w')
        self.recoveryGraph.setBackground('w')
        self.signal_title = None
        self.signal_data_t = None
        self.signal_data_y = None
        self.from_csv = False
        self.sample_freq = 0
        self.csv_freq = 0
        self.mixer_signals = {}
        self.handle_buttons()
        self.is_noisy = False
        self.noisy_signal = None

        # allow only integers in lineEdits
        only_int = QIntValidator()
        only_int.setRange(0, 999999)
        self.lineEditMagnitude.setValidator(only_int)
        self.lineEditPhase.setValidator(only_int)
        only_int.setRange(0, 500)
        self.lineEditFrequency.setValidator(only_int)

        # Noise slider
        self.noiseSlider.setMinimum(1)
        self.noiseSlider.setMaximum(50)
        self.noiseSlider.setSingleStep(5)
        self.noiseSlider.setValue(25)
        self.noiseSlider.setTickPosition(QSlider.TicksAbove)

    def handle_buttons(self):
        self.importSignalBtn.clicked.connect(self.import_from_csv)
        self.importFromMixerBtn.clicked.connect(self.import_from_mixer)
        self.addSineToMixerBtn.clicked.connect(self.add_to_mixer)
        self.removeSignalMixerBtn.clicked.connect(self.remove_from_mixer)
        self.showSampleFreqBtn.clicked.connect(self.sample_signal)
        self.noiseSlider.valueChanged.connect(self.update_snr)
        self.noiseBtn.setCheckable(True)
        self.noiseBtn.toggled.connect(self.is_noisy)
        self.noiseBtn.setEnabled(False)
        self.noiseSlider.setEnabled(False)


    def import_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "open csv file", "data/", "CSV Files (*.csv)")
        if file_path != '':
            self.signal_title = file_path.split("/")[-1][:-4]
            print(self.signal_title)
            signal_data = read_csv(file_path)
            self.signal_data_t, self.signal_data_y = signal_data.values[:, 0], signal_data.values[:, 1]

            plot(self.signal_data_t, self.signal_data_y, self.signal_title, self.samplingGraph)
            # plot(self.signal_data_t, self.signal_data_y, self.signal_title, self.samplingGraph)
            # plot(self.signal_data_t, self.signal_data_y, self.signal_title, self.samplingGraph)

            self.from_csv = True
            self.csv_freq = 125
            self.noiseBtn.setEnabled(True)

        else:
            QMessageBox.warning(self, "Warning", "No file selected")

    def import_from_mixer(self):
        self.signal_data_t = np.linspace(0, 1, 1000)
        self.signal_data_y = np.zeros(1000)
        for signal in self.mixer_signals:
            self.signal_data_y += self.mixer_signals[signal][0] * np.sin(
                2 * np.pi * self.mixer_signals[signal][2] * self.signal_data_t + self.mixer_signals[signal][
                    1] / 180 * np.pi)
        plot(self.signal_data_t, self.signal_data_y, self.signal_title, self.samplingGraph)
        self.mixer_signals.clear()
        self.comboBoxMixer.clear()
        self.mixerGraph.clear()
        self.from_csv = False
        self.noiseBtn.setEnabled(True)

    def add_to_mixer(self):
        if (self.lineEditMagnitude.text() != '' and self.lineEditPhase.text() != '' and
                self.lineEditFrequency.text() != '' and self.lineEditTitle.text() != ''):
            title = self.lineEditTitle.text()
            while title in self.mixer_signals:
                title += "_"
            else:
                self.mixer_signals[title] = [
                    float(self.lineEditMagnitude.text()),
                    float(self.lineEditPhase.text()),
                    float(self.lineEditFrequency.text())
                ]
                self.comboBoxMixer.addItem(title)
                self.build_mixer_graph()
                self.lineEditTitle.clear()
                self.lineEditMagnitude.clear()
                self.lineEditPhase.clear()
                self.lineEditFrequency.clear()
        else:
            QMessageBox.warning(self, "Warning", "Please fill all the fields")

    def remove_from_mixer(self):
        self.mixer_signals.pop(self.comboBoxMixer.currentText())
        self.comboBoxMixer.removeItem(self.comboBoxMixer.currentIndex())
        self.build_mixer_graph()
        if len(self.mixer_signals) == 0:
            self.mixerGraph.clear()

    def build_mixer_graph(self):
        self.mixerGraph.clear()
        t = np.linspace(0, 1, 1000)
        y = np.zeros(1000)
        for signal in self.mixer_signals:
            y += self.mixer_signals[signal][0] * np.sin(
                2 * np.pi * self.mixer_signals[signal][2] * t + self.mixer_signals[signal][1] / 180 * np.pi)
        plot(t, y, "Mixer", self.mixerGraph)

    def sample_signal(self):
        if self.from_csv:
            self.sample_freq = self.csv_freq
        else:
            max_frequency = calculate_max_frequency(self.signal_data_y)
            sampling_frequency = 2 * max_frequency
            print(f"Maximum Frequency: {max_frequency} Hz")
            print(f"Sampling Frequency (Nyquist Theorem): {sampling_frequency} Hz")

    def add_noise(self, snr):
        self.samplingGraph.clear()
        self.recoveryGraph.clear()
        self.diffGraph.clear()

        power = self.signal_data_y ** 2
        signal_average_power = np.mean(power)
        signal_average_power_db = 10 * np.log10(signal_average_power)
        noise_power_db = signal_average_power_db - snr
        noise_power_watts = 10 ** (noise_power_db / 10)
        added_noise = np.random.normal(0, np.sqrt(noise_power_watts), len(self.signal_data_y))
        self.noisy_signal = self.signal_data_y + added_noise
        plot(self.signal_data_t, self.noisy_signal, self.signal_title, self.samplingGraph, p='r')

    def update_snr(self):
        if self.is_noisy:
            snr = self.noiseSlider.value()
            self.noiseLabel.setText(f'SNR: {snr} dB')
            self.add_noise(snr)

    def is_noisy(self):
        if self.noiseBtn.isChecked():
            self.noiseSlider.setEnabled(True)
            self.is_noisy = True
            self.update_snr()

        else:
            plot(self.signal_data_t, self.signal_data_y, self.signal_title, self.samplingGraph)
            self.noiseSlider.setEnabled(False)
            self.is_noisy = False

        # def sample_signal(self):
        #     if self.is_noisy:
        #         use noisy signal data
        #     else:
        #         use original signal data

def main():
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
