from PyQt5.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QApplication, QSlider
import pyqtgraph as pg
from PyQt5.uic import loadUiType
from pandas import read_csv
import sys
from PyQt5.QtGui import QIntValidator
import numpy as np
from os import path

FORM_CLASS, _ = loadUiType(path.join(path.dirname(__file__), "mainWindow.ui"))


def graph_setup(graph):
    graph.addLegend(labelTextSize='10pt')
    signal = pg.PlotCurveItem()
    graph.addItem(signal)
    return signal


def sampling(t, y, sampling_frequency):
    y1, t1 = y, t
    num_samples = int(sampling_frequency * t[-1])
    num_point = len(t) - 1
    while num_point % (num_samples - 1) != 0:
        num_point += 1
    if num_point != len(t) - 1:
        t1, y1 = recovery(y, t, t[-1], num_points=num_point + 1)
    index = np.round(np.linspace(0, num_point, num_samples)).astype(int)
    samples_time, samples_y = t1[index], y1[index]
    return samples_time, samples_y


def recovery(y, t, time_of_signal, num_points=1001):
    recovered_t = np.linspace(0, time_of_signal, num_points)
    time_of_point = t[1] - t[0]
    sinc_denominator = np.tile(recovered_t, (len(t), 1)) - np.tile(t[:, np.newaxis], (1, len(recovered_t)))
    recovered_y = np.dot(y, np.sinc(sinc_denominator / time_of_point))
    return recovered_t, recovered_y


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
        self.mixer_signals = {}
        self.handle_buttons()
        self.is_noisy = False
        self.noisy_signal = None
        self.max_freq = None

        self.original_signal = graph_setup(self.samplingGraph)
        self.recovered_signal = graph_setup(self.recoveryGraph)
        self.diff_signal = graph_setup(self.diffGraph)
        self.mixer_signal = graph_setup(self.mixerGraph)
        self.sampling_scatter = pg.ScatterPlotItem()
        self.samplingGraph.addItem(self.sampling_scatter)

        self.recoveryGraph.setXLink(self.samplingGraph)
        self.recoveryGraph.setYLink(self.samplingGraph)
        self.diffGraph.setXLink(self.samplingGraph)

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
        self.samplingFrequencySlider.setTickPosition(QSlider.TicksAbove)

    def graphs_plot(self, t, y, p="b"):
        if self.samplingFrequencySlider.value() != 0:
            samples_t, samples_y = sampling(t, y, self.samplingFrequencySlider.value())
            recovered_t, recovered_y = recovery(samples_y, samples_t, self.signal_data_t[-1])
            difference = np.subtract(y, recovered_y)
            self.samplingGraph.setLimits(xMin=min(t) - 0.2, xMax=max(t) + 0.2, yMin=min(y) - 0.2, yMax=max(y) + 0.2)
            self.recoveryGraph.setLimits(xMin=min(t) - 0.2, xMax=max(t) + 0.2, yMin=min(y) - 0.2, yMax=max(y) + 0.2)
            self.diffGraph.setLimits(xMin=min(t), xMax=max(t), yMin=2 * min(difference) - 2,
                                     yMax=2 * max(difference) + 2)
            self.diffGraph.setYRange(min=2 * min(difference) - 0.5, max=2 * max(difference) + 0.5)
            self.original_signal.setData(t, y, pen=p, name=self.signal_title)
            self.sampling_scatter.setData(samples_t, samples_y, pen="black", name="samples", symbol="x")
            self.recovered_signal.setData(recovered_t, recovered_y, pen="b", name=f'recovered {self.signal_title}')
            self.diff_signal.setData(t, difference, pen="r", ame="difference")
        else:
            self.original_signal.setData(t, y, pen=p, name=self.signal_title)
            self.sampling_scatter.setData()
            self.recovered_signal.setData()
            self.diff_signal.setData()

    def handle_buttons(self):
        self.importSignalBtn.clicked.connect(self.import_from_csv)
        self.importFromMixerBtn.clicked.connect(self.import_from_mixer)
        self.addSineToMixerBtn.clicked.connect(self.add_to_mixer)
        self.removeSignalMixerBtn.clicked.connect(self.remove_from_mixer)
        self.noiseSlider.valueChanged.connect(self.update_snr)
        self.noiseBtn.setCheckable(True)
        self.noiseBtn.toggled.connect(self.check_noisy)
        self.noiseBtn.setEnabled(False)
        self.noiseSlider.setEnabled(False)
        self.samplingFrequencySlider.setEnabled(False)
        self.frequencyComboBox.currentTextChanged.connect(self.frequency_change)
        self.samplingFrequencySlider.valueChanged.connect(self.frequency_change)

    def import_from_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "open csv file", "data/", "CSV Files (*.csv)")
        if file_path != '':
            self.signal_title = file_path.split("/")[-1][:-4]
            signal_data = read_csv(file_path)
            self.signal_data_t, self.signal_data_y = signal_data.values[:, 0], signal_data.values[:, 1]
            # calculate max frequency
            i = 0
            while self.signal_data_t[i] < 1:
                i += 1
            self.max_freq = i / 2
            self.noiseBtn.setEnabled(True)
            self.samplingFrequencySlider.setEnabled(True)
            self.samplingFrequencySlider.setMinimum(0)
            self.samplingFrequencySlider.setMaximum(int(self.max_freq * 4))
            self.samplingFrequencySlider.setSingleStep(5)
            self.samplingFrequencySlider.setValue(int(self.max_freq * 2))
            self.samplingFrequencySlider.setTickPosition(QSlider.TicksAbove)
            self.frequency_change()
            self.graphs_plot(self.signal_data_t, self.signal_data_y)
            self.check_noisy()
        else:
            QMessageBox.warning(self, "Warning", "No file selected")

    def import_from_mixer(self):
        self.signal_data_t = np.linspace(0, 1, 1001)
        self.signal_data_y = np.zeros(1001)
        self.max_freq = 0
        for signal in self.mixer_signals:
            if self.mixer_signals[signal][2] > self.max_freq:
                self.max_freq = self.mixer_signals[signal][2]
            self.signal_data_y += self.mixer_signals[signal][0] * np.sin(
                2 * np.pi * self.mixer_signals[signal][2] * self.signal_data_t + self.mixer_signals[signal][
                    1] / 180 * np.pi)

        self.noiseBtn.setEnabled(True)
        self.samplingFrequencySlider.setEnabled(True)
        self.samplingFrequencySlider.setMinimum(0)
        self.samplingFrequencySlider.setMaximum(int(self.max_freq * 4))
        self.samplingFrequencySlider.setSingleStep(5)
        self.samplingFrequencySlider.setValue(int(self.max_freq * 2))
        self.samplingFrequencySlider.setTickPosition(QSlider.TicksAbove)
        self.frequency_change()
        self.graphs_plot(self.signal_data_t, self.signal_data_y)
        self.mixer_signals.clear()
        self.comboBoxMixer.clear()
        self.mixer_signal.setData()
        self.noiseBtn.setEnabled(True)
        self.check_noisy()

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
            self.mixer_signal.setData()

    def build_mixer_graph(self):
        t = np.linspace(0, 1, 1001)
        y = np.zeros(1001)
        for signal in self.mixer_signals:
            y += self.mixer_signals[signal][0] * np.sin(
                2 * np.pi * self.mixer_signals[signal][2] * t + self.mixer_signals[signal][1] / 180 * np.pi)
        self.mixer_signal.setData(t, y, title="Mixer", pen='b')

    def add_noise(self, snr):
        power = self.signal_data_y ** 2
        signal_average_power = np.mean(power)
        signal_average_power_db = 10 * np.log10(signal_average_power)
        noise_power_db = signal_average_power_db - snr
        noise_power_watts = 10 ** (noise_power_db / 10)
        added_noise = np.random.normal(0, np.sqrt(noise_power_watts), len(self.signal_data_y))
        self.noisy_signal = self.signal_data_y + added_noise
        self.graphs_plot(self.signal_data_t, self.noisy_signal, p='r')

    def update_snr(self):
        if self.is_noisy:
            snr = self.noiseSlider.value()
            self.noiseLabel.setText(f'SNR: {snr} dB')
            self.add_noise(snr)

    def check_noisy(self):
        if self.noiseBtn.isChecked():
            self.noiseSlider.setEnabled(True)
            self.is_noisy = True
            self.update_snr()

        else:
            self.graphs_plot(self.signal_data_t, self.signal_data_y)
            self.noiseSlider.setEnabled(False)
            self.is_noisy = False

    def frequency_change(self):
        frequency_type = self.frequencyComboBox.currentIndex()
        if frequency_type == 0:
            self.frequencyLabel.setText(f'Frequency: {self.samplingFrequencySlider.value()} Hz')
        else:
            self.frequencyLabel.setText(f'Frequency: {self.samplingFrequencySlider.value() / self.max_freq} Fmax')
        if self.is_noisy:
            self.graphs_plot(self.signal_data_t, self.noisy_signal, p='r')
        else:
            self.graphs_plot(self.signal_data_t, self.signal_data_y)


def main():
    app = QApplication(sys.argv)
    window = MainApp()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()
