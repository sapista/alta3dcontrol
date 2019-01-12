#!/usr/bin/env python
# encoding: utf-8

import gtk
import time
import GCodeSerialSender
from GCodeSerialSender import GCodePrinterSerialSender

import threading
import gobject
gobject.threads_init()


"""
NOTES ON SERIAL PORT EMULATION

3 terminals are needed + the socat program

1. in terminal one: 
socat -d -d pty,raw,echo=0 pty,raw,echo=0

2. in terminal two: Grab all gcodes send to the printer
cat < /dev/pts/2

3. in terminal three: Emulate printer answers "ok"
echo "ok" > /dev/pts/2 

This python program must be connected to /dev/pts/1 in this example

NOTES ON REAL SERIAL PORT ON LINUX

make sure to add your user to uucp group:

sudo gpasswd -a sapista uucp
"""


class AltaControlGUI(gobject.GObject):
    __gsignals__ = {
        'serial_thread_end': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                (gobject.TYPE_BOOLEAN,))
    }

    _printer_connection=False
    _GCODE_FILE_CALIBRATION_BACK = "gcode files/CalibBackPoint.gcode"
    _GCODE_FILE_CALIBRATION_FRONTLEFT = "gcode files/CalibFrontLeft.gcode"
    _GCODE_FILE_CALIBRATION_FRONTRIGHT = "gcode files/CalibFrontRight.gcode"
    _GCODE_FILE_FILAMENT_LOAD = "gcode files/LoadFilament.gcode"
    _GCODE_FILE_FILAMENT_UNLOAD = "gcode files/UnloadFilament.gcode"

    _current_temp = "" #Used to continuously display current temperature
    _serial_thread_running = False

    def delete_event(self, widget, event, data=None):
        if self._printer_connection.__class__.__name__ == 'GCodePrinterSerialSender':
            self._printer_connection.write("M104 S20") #Ensure to turn off the heater
            self._printer_connection.close()
        return False

    def destroy(self, widget, data=None):
        gtk.main_quit()

    def btn_home_clicked(self, widget, data=None):
        print "going home..."
        self._printer_connection.write("G28")

    def btn_connect_clicked(self, widget, data=None):
        if self.btn_connect.get_active():
            print "opening serial port..."
            self.btn_connect.set_label("Connecting...")
            try:
                self._printer_connection = GCodePrinterSerialSender(self.ety_sport.get_text(), self.spin_baudrate.get_value() )
            except:
                self.btn_connect.set_label("Connect to the printer")
                self.btn_connect.set_active(False)
                print "Error: Cannot connect to the printer"
                return

            time.sleep(1)
            self.btn_connect.set_label("Disconnect")
            self.lbl_online.set_markup("<span foreground=\"green\" size=\"x-large\">Connected</span>")
            self.btn_home.set_sensitive(True)
            self.frm_calibration.set_sensitive(True)
            self.frm_filament.set_sensitive(True)
            self.frm_temp.set_sensitive(True)
            self._printer_connection.connect('temperature_message', self.temperature_message_received, None)


        elif self._printer_connection.__class__.__name__ == 'GCodePrinterSerialSender':
            print "closeing serial port..."
            self._printer_connection.close()
            self._printer_connection = False
            self.btn_connect.set_label("Connect to the printer")
            self.lbl_online.set_markup("")
            self.btn_home.set_sensitive(False)
            self.frm_calibration.set_sensitive(False)
            self.frm_filament.set_sensitive(False)
            self.frm_temp.set_sensitive(False)

    def btn_rungcode_clicked(self, widget, data=None):
        self.btn_home.set_sensitive(False)
        self.frm_calibration.set_sensitive(False)
        self.frm_filament.set_sensitive(False)
        self.frm_temp.set_sensitive(False)
        self._serial_thread_running = True
        t = threading.Thread(target=self.send_gcode_file, args=(data,))
        t.start()
        return

    def send_gcode_file(self, fname):
        if self._printer_connection.__class__.__name__ != 'GCodePrinterSerialSender':
            raise Exception("The 3d printer is not connected")
            self._serial_thread_running = False

        gf = open(fname, "r")
        for x in gf:
           self._printer_connection.write(x)
        gf.close()
        self.emit('serial_thread_end', True) #Emit a signal once the serial port thread ends

    def serial_thred_end_callback(self, widget, bEnd, data=None):
        if self._printer_connection.__class__.__name__ == 'GCodePrinterSerialSender':
            self.btn_home.set_sensitive(True)
            self.frm_calibration.set_sensitive(True)
            self.frm_filament.set_sensitive(True)
            self.frm_temp.set_sensitive(True)
        self._serial_thread_running = False

    def tempMeasurment(self):
        if self._printer_connection.__class__.__name__ == 'GCodePrinterSerialSender' and not self._serial_thread_running:
            current_temp = self._printer_connection.write("M105")
            current_temp = current_temp.strip()
            current_temp = current_temp.replace(' ', '')
            current_temp_splited = current_temp.split("T:")
            if len(current_temp_splited) >= 2:
                current_temp = current_temp_splited[1]
                self._current_temp = current_temp.split("/")[0]

        self.lbl_tempMon.set_label(self._current_temp + "ºC")
        return True #To keep timer alive

    def temperature_message_received(self, widget, temperature, data=None):
        self._current_temp = temperature

    def spin_temp_changed(self, event):
        if self._printer_connection.__class__.__name__ == 'GCodePrinterSerialSender':
            self._printer_connection.write("M104 S" + str(self.spin_temp.get_value()))

    def __init__(self):
        self.__gobject_init__()

        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.vbox_top = gtk.VBox()
        self.hbox_top = gtk.HBox()

        self.lbl_sport = gtk.Label("Serial Port:")
        self.ety_sport = gtk.Entry()
        self.ety_sport.set_text("/dev/ttyUSB0")

        self.adj_baudrate = gtk.Adjustment(1.0, 1.0, 12.0, 1.0, 5.0, 0.0)
        self.spin_baudrate = gtk.SpinButton(self.adj_baudrate, 0, 0)
        self.spin_baudrate.set_wrap(True)
        self.spin_baudrate.set_range(100, 500000)
        self.spin_baudrate.set_value(250000)

        self.btn_connect = gtk.ToggleButton("Connect to the printer")
        self.lbl_online = gtk.Label()

        self.btn_home = gtk.Button("Go Home!")
        self.btn_CalibrateFrontLeft = gtk.Button("Front-Left")
        self.btn_CalibrateFrontRight = gtk.Button("Front-Right")
        self.btn_CalibrateBackCenter = gtk.Button("Back-Center")

        self.vbox_calibration = gtk.VBox()
        self.hbox_calibration = gtk.HBox()

        self.hbox_top.pack_start(self.lbl_sport, expand=False, fill=False)
        self.hbox_top.pack_start(self.ety_sport, expand=False, fill=False)
        self.hbox_top.pack_start(self.spin_baudrate, expand=False, fill=False)
        self.hbox_top.pack_start(self.btn_connect, expand=False, fill=False)
        self.hbox_top.pack_start(self.lbl_online, expand=False, fill=False)
        self.hbox_top.pack_end(self.btn_home, expand=False, fill=False)
        self.vbox_top.pack_start(self.hbox_top, expand=False, fill=False)

        self.hbox_calfiltemp = gtk.HBox()

        #Calibration GUI
        self.frm_calibration = gtk.Frame("Calibration")
        self.alng_calibration = gtk.Alignment(0.5, 0.5, 0.5, 0.5)
        self.alng_calibration.add(self.frm_calibration)
        self.frm_calibration.add(self.vbox_calibration)
        self.alng_calback = gtk.Alignment(0.5, 0)
        self.alng_calback.add(self.btn_CalibrateBackCenter)
        self.alng_calfront = gtk.Alignment(0.5, 0, 0.5)
        self.alng_calfront.add(self.hbox_calibration)
        self.vbox_calibration.pack_start(self.alng_calback, expand=False, fill=False)
        self.vbox_calibration.pack_start(self.alng_calfront, expand=True, fill=False)
        self.hbox_calibration.pack_start(self.btn_CalibrateFrontLeft, expand=False, fill=False)
        self.hbox_calibration.pack_end(self.btn_CalibrateFrontRight, expand=False, fill=False)
        self.hbox_calfiltemp.pack_start(self.alng_calibration, expand=True, fill=True)

        #Filament GUI
        self.frm_filament = gtk.Frame("Filament Load/Unload")
        self.alng_filament = gtk.Alignment(0.5, 0.5, 0.5, 0.5)
        self.alng_filament.add(self.frm_filament)
        self.vbox_filament = gtk.VBox()
        self.btn_filamentLoad = gtk.Button("Load Filament")
        self.btn_filamentUnload = gtk.Button("Unload Filament")
        self.vbox_filament.pack_start(self.btn_filamentLoad, expand=False, fill=False)
        self.vbox_filament.pack_end(self.btn_filamentUnload, expand=False, fill=False)
        self.frm_filament.add(self.vbox_filament)
        self.hbox_calfiltemp.pack_start(self.alng_filament, expand=True, fill=False)

        #Temperature monitor GUI
        self.frm_temp = gtk.Frame("Heater Control")
        self.alng_temp = gtk.Alignment(0.5, 0.5, 0.5, 0.5)
        self.alng_temp.add(self.frm_temp)
        self.vbox_temp = gtk.VBox()
        self.frm_temp.add(self.vbox_temp)
        self.hbox_tempMon = gtk.HBox()
        self.vbox_temp.pack_start(self.hbox_tempMon)
        self.lbl_temp = gtk.Label("Temperature:")
        self.hbox_tempMon.pack_start(self.lbl_temp)
        self.lbl_tempMon = gtk.Label("---")
        self.hbox_tempMon.pack_start(self.lbl_tempMon)
        self.hbox_tempSet = gtk.HBox()
        self.lbl_tempSet = gtk.Label("Set temperature:")
        self.spin_temp = gtk.SpinButton( digits=1)
        self.spin_temp.set_range(0.0, 250.0)
        self.spin_temp.set_value(15.0)
        self.hbox_tempSet.pack_start(self.lbl_tempSet)
        self.hbox_tempSet.pack_start(self.spin_temp)
        self.vbox_temp.pack_start(self.hbox_tempSet)
        self.hbox_calfiltemp.pack_start(self.alng_temp)

        self.vbox_top.pack_start(self.hbox_calfiltemp)

        self.window.add(self.vbox_top)
        self.window.set_size_request(650, 300)
        self.window.show_all()

        self.btn_home.connect("clicked", self.btn_home_clicked, None)
        self.btn_connect.connect("toggled", self.btn_connect_clicked, None)
        self.btn_CalibrateBackCenter.connect("clicked", self.btn_rungcode_clicked, self._GCODE_FILE_CALIBRATION_BACK)
        self.btn_CalibrateFrontRight.connect("clicked", self.btn_rungcode_clicked, self._GCODE_FILE_CALIBRATION_FRONTRIGHT)
        self.btn_CalibrateFrontLeft.connect("clicked", self.btn_rungcode_clicked, self._GCODE_FILE_CALIBRATION_FRONTLEFT)
        self.btn_filamentLoad.connect("clicked", self.btn_rungcode_clicked, self._GCODE_FILE_FILAMENT_LOAD)
        self.btn_filamentUnload.connect("clicked", self.btn_rungcode_clicked, self._GCODE_FILE_FILAMENT_UNLOAD)
        self.spin_temp.connect("value-changed", self.spin_temp_changed)

        self.connect("serial_thread_end", self.serial_thred_end_callback)
        self.window.connect("destroy", self.destroy)
        self.window.connect("delete_event", self.delete_event)

        self.TemperatureMeasureTimer = gtk.timeout_add(1000, self.tempMeasurment)

        self.btn_home.set_sensitive(False)
        self.frm_calibration.set_sensitive(False)
        self.frm_filament.set_sensitive(False)
        self.frm_temp.set_sensitive(False)


    def main(self):
        gtk.main()


print __name__
if __name__ == "__main__":
    base = AltaControlGUI()
    base.main()