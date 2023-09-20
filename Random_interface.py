
import sys, os
from PyQt5 import QtWidgets, QtCore, uic
from PyQt5.QtWidgets import QFileDialog, QInputDialog
import pyqtgraph as pg
import pandas as pd
import numpy as np

import time
from datetime import datetime
import threading as th
import serial
import json
import itertools
import random

class Acquisition(QtWidgets.QMainWindow):
    def __init__(self):
        super(Acquisition, self).__init__()
        uic.loadUi('UI_files/Random_interface.ui', self)
        self.setStyleSheet("background-color: white;")

        layout_row = 9,2,3,2,3,4,9,2
        layout_col = 5,5,3

        for i,r in enumerate(layout_row):
            self.geiger_grid.setRowStretch(i,r)
        for i,c in enumerate(layout_col):
            self.geiger_grid.setColumnStretch(i,c)
        
        ### Defining all data structures we need
        
        self.running = True

        # self.scanButton.clicked.connect(self.start_recording)

        self.PulsePlot_geiger.setTitle('Pulses')
        self.PulsePlot_geiger.setLabel('bottom',text='Time [s]')
        self.PulsePlot_geiger.hideAxis('left')
        

        self.NumberPlot_geiger.setTitle('Distribution')
        self.NumberPlot_geiger.setLabel('bottom',text='Number')
        self.NumberPlot_geiger.setLabel('left',text='Counts')

        self.pen = pg.mkPen(color=(255, 0, 0), width=3, style=QtCore.Qt.SolidLine)
        # self.NumberPlot_geiger.setStyleSheet("border : 5px solid green;" "padding : 5px;")

        self.geiger_clearButton.clicked.connect(self.clear_data)
        self.geiger_save.clicked.connect(self.save_geiger_dist)
        self.geiger_load.clicked.connect(self.load_geiger_dist)
        self.pseudo_random.clicked.connect(self.gen_pseudo_random)

        self.delta_pulses = []
        self.current_pulses = []
        self.prev_delta = 0
        self.last_delta = 0
        self.last_random_bit = 0
        self.last_random_byte = 0
        self.random_generated_bytes = []

        # digit counter
        self.digit = 0

        self.bits_number = 8

        self.geiger_lastdt.setDecMode()
        self.geiger_prevdt.setDecMode()
        self.geiger_randbit.setBinMode()
        self.geiger_randbyte.setBinMode()
        self.geiger_randdec.setDecMode()
        
        self.geiger_lastdt.setDigitCount(5)
        self.geiger_prevdt.setDigitCount(5)
        self.geiger_randbit.setDigitCount(1)
        self.geiger_randbyte.setDigitCount(self.bits_number)
        self.geiger_randdec.setDigitCount(3)



        self.x_pulse = [0]
        self.y_pulse = [0]

        self.clear_data()
        self.clear_plot()

        ## start all the timers and threads

        self.geigerThread = th.Thread(target = self.read_geiger)
        self.geigerThread.setDaemon(True)
        self.geigerThread.start()

        self.update_plotsTimer = QtCore.QTimer()
        self.update_plotsTimer.timeout.connect(self.update_plots)
        self.update_plotsTimer.setInterval(1000)
        self.update_plotsTimer.start()

        self.processTimer = QtCore.QTimer()
        self.processTimer.timeout.connect(self.process)
        self.processTimer.setInterval(100)
        self.processTimer.start()
        
        self.show()

    def gen_pseudo_random(self):
        for i in range(1000000):
            self.random_generated_bytes.append(random.randint(0,(2**self.bits_number)-1))
        pass

    def save_geiger_dist(self):
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
            "Save File", "", "All Files(*);;Binary files (*.bin)")
        if fileName:
            with open(fileName, 'wb') as f:
                for byte in self.random_generated_bytes:
                    f.write(byte.to_bytes(1, byteorder='big'))
                # np.savetxt(f,self.random_generated_bytes)                
        return

    def load_geiger_dist(self):
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, 
            "Load File", "",  "All Files(*);;Binary files (*.bin)")
        if fileName:
            with open(fileName, 'rb') as f:
                self.random_generated_bytes = []

                while (byte := f.read(1)):
                    self.random_generated_bytes.append(int.from_bytes(byte, byteorder='big'))
        return
    
    def read_geiger(self):
        while self.running:
            # while True:
            #     self.current_pulses.append(random.randint(0,10000))

            #     time.sleep(0.001)
            
            # pass
            try:
                ser = serial.Serial('/dev/ttyACM0', 9600, timeout=0.1)         # 1/timeout is the frequency at which the port is read
                while True:
                    
                    data = ser.readline().decode().strip()
                    if data:
                        self.current_pulses.append(int(data))
            except:
                # print("failed read")
                pass

    def append_plot_lists(self):
        total = sum(self.delta_pulses)

        if len(self.y_pulse)>5000:
            self.y_pulse = self.y_pulse[-5000:]
            self.x_pulse = self.x_pulse[-5000:]

        total_10ms = int(total/10)
        last_index = len(self.y_pulse)-1

        for i in range(0,total_10ms):
            self.x_pulse.append(self.x_pulse[-1]+1)
            self.y_pulse.append(0)
        
        for i in self.delta_pulses:
            index = int(i/10)
            self.y_pulse[last_index+index] = 1

        
        
        pass

    def update_displays(self):
        

        for i in range(len(self.delta_pulses)//2):
            
            self.prev_delta = self.delta_pulses[i*2]
            self.last_delta = self.delta_pulses[1+i*2]
            self.last_random_bit = 1 if (self.last_delta-self.prev_delta) > 0 else  0
            self.geiger_lastdt.display(self.last_delta)
            self.geiger_prevdt.display(self.prev_delta)
            self.geiger_randbit.display(self.last_random_bit)
            self.update_random_byte()

        self.delta_pulses = []
            

        pass

    def update_random_byte(self):
        if self.digit == self.bits_number:
            self.digit = 0 

            self.random_generated_bytes.append(self.last_random_byte)

            log = 'Last number -> [binary] {:08b}  --- [decimal] {:03d}'.format(self.last_random_byte,self.last_random_byte)

            self.geiger_log.append(log)
            self.last_random_byte = 0 

        self.last_random_byte += self.last_random_bit*2**self.digit
        self.geiger_randbyte.display('{:08b}'.format(self.last_random_byte))
        self.geiger_randdec.display(self.last_random_byte)
        self.digit+=1
        pass
        
    def update_plots(self):
        self.PulsePlot_geiger.clear()
        self.PulsePlot_geiger.plot(np.array(self.x_pulse)/100,self.y_pulse,pen=self.pen)
        y,x = np.histogram(self.random_generated_bytes, bins=np.linspace(-0.5, (2**self.bits_number)-0.5, (2**self.bits_number)+1))
        
        self.NumberPlot_geiger.clear()
        self.NumberPlot_geiger.plot(x,y,stepMode=True,pen=self.pen)

        pass

    def process(self):
        
        if len(self.current_pulses)%2:
            
            self.delta_pulses = self.current_pulses
            self.current_pulses = []
            self.append_plot_lists()
            self.update_displays()
                   
            
        pass
    

    def clear_data(self):
        self.current_pulses = [] 
        self.prev_delta = 0
        self.last_delta = 0
        self.last_random_bit = 0 
        self.last_random_byte = 0
        self.last_random_decimal = 0
        self.random_generated_bytes = []
        self.random_generated_decimals = []

        self.digit = 0

        self.x_pulse = [0]
        self.y_pulse = [0]
        self.PulsePlot_geiger.clear()
        self.NumberPlot_geiger.clear()

        pass

    def clear_plot(self):
        pass

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    pg.setConfigOption('background', 'w')
    pg.setConfigOption('foreground', 'k')

    window = Acquisition()
    sys.exit(app.exec_())
