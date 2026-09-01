import sys
import os
import json
from datetime import datetime, timedelta
from collections import deque
import numpy as np
import time

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QComboBox, QCheckBox, QPushButton, 
                             QGroupBox, QTabWidget, QLineEdit, QFileDialog, QMessageBox, 
                             QGridLayout)
from PyQt6.QtWidgets import QDialog
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QColor, QPalette

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.gridspec as gridspec
import matplotlib.dates as mdates
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.widgets import MultiCursor

import serial.tools.list_ports

from sensor_thread import SensorThread
from data_logger import DataLogger
from sensor_driver import TB200BSensor
from adam_driver import adam_manager

class SensorConfigPanel(QGroupBox):
    def __init__(self, sensor_id, parent=None):
        super().__init__(f"Sensor {sensor_id}", parent)
        self.sensor_id = sensor_id
        
        layout = QVBoxLayout()
        
        # Port
        h1 = QHBoxLayout()
        h1.addWidget(QLabel("Port:"))
        self.cmb_port = QComboBox()
        h1.addWidget(self.cmb_port)
        
        self.lbl_serial = QLabel("SN: N/A")
        self.lbl_serial.setStyleSheet("color: gray;")
        h1.addWidget(self.lbl_serial)
        
        self.btn_ident = QPushButton("Identify (Off)")
        self.btn_ident.setCheckable(True)
        h1.addWidget(self.btn_ident)
        
        layout.addLayout(h1)
        
        # Sensor Info Label
        h_info = QHBoxLayout()
        self.lbl_info = QLabel("Sensor Info: N/A")
        self.lbl_info.setStyleSheet("color: darkblue; font-style: italic;")
        h_info.addWidget(self.lbl_info)
        layout.addLayout(h_info)
        
        # Brand and Gas
        h2 = QHBoxLayout()
        h2.addWidget(QLabel("Brand:"))
        self.cmb_brand = QComboBox()
        self.cmb_brand.addItems(["ECSense", "Membrapor"])
        h2.addWidget(self.cmb_brand)
        
        h2.addWidget(QLabel("Gas:"))
        self.cmb_gas = QComboBox()
        self.cmb_gas.addItems(["CO", "H2", "O2"])
        h2.addWidget(self.cmb_gas)
        layout.addLayout(h2)

        # Membrapor Analog Settings (Hidden by default)
        self.w_membrapor = QWidget()
        h_mem = QHBoxLayout(self.w_membrapor)
        h_mem.setContentsMargins(0, 0, 0, 0)
        
        h_mem.addWidget(QLabel("Model:"))
        self.cmb_adam_model = QComboBox()
        self.cmb_adam_model.addItems(["ADAM-4017+", "ADAM-4019+"])
        h_mem.addWidget(self.cmb_adam_model)
        
        h_mem.addWidget(QLabel("Ch:"))
        self.cmb_adam_ch = QComboBox()
        self.cmb_adam_ch.addItems([str(i) for i in range(8)])
        h_mem.addWidget(self.cmb_adam_ch)
        
        h_mem.addWidget(QLabel("Base mV:"))
        self.txt_base_val = QLineEdit("0.0")
        self.txt_base_val.setFixedWidth(40)
        h_mem.addWidget(self.txt_base_val)
        
        h_mem.addWidget(QLabel("Max mV:"))
        self.txt_max_val = QLineEdit("30.0")
        self.txt_max_val.setFixedWidth(40)
        h_mem.addWidget(self.txt_max_val)
        
        h_mem.addWidget(QLabel("Max Gas:"))
        self.txt_max_gas = QLineEdit("100")
        self.txt_max_gas.setFixedWidth(50)
        h_mem.addWidget(self.txt_max_gas)
        
        layout.addWidget(self.w_membrapor)
        self.w_membrapor.hide()
        
        # Membrapor Calibration Live Display
        self.w_membrapor_live = QWidget()
        h_live = QHBoxLayout(self.w_membrapor_live)
        h_live.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_live_mv = QLabel("Live: -- mV")
        self.lbl_live_mv.setStyleSheet("font-weight: bold; color: darkgreen;")
        h_live.addWidget(self.lbl_live_mv)
        
        self.lbl_avg_mv = QLabel("60s Avg: -- mV")
        self.lbl_avg_mv.setStyleSheet("font-weight: bold; color: darkblue;")
        h_live.addWidget(self.lbl_avg_mv)
        
        self.lbl_std_mv = QLabel("60s Std: -- mV")
        self.lbl_std_mv.setStyleSheet("font-weight: bold; color: darkred;")
        h_live.addWidget(self.lbl_std_mv)
        
        layout.addWidget(self.w_membrapor_live)
        self.w_membrapor_live.hide()
        
        # Toggles
        h3 = QHBoxLayout()
        self.chk_plot_gas = QCheckBox("Plot Gas")
        self.chk_plot_temp = QCheckBox("Plot Temp")
        self.chk_plot_hum = QCheckBox("Plot Hum")
        self.chk_plot_gas.setChecked(True)
        self.chk_plot_temp.setChecked(True)
        self.chk_plot_hum.setChecked(True)
        h3.addWidget(self.chk_plot_gas)
        h3.addWidget(self.chk_plot_temp)
        h3.addWidget(self.chk_plot_hum)
        layout.addLayout(h3)
        
        self.setLayout(layout)
        
        self.cmb_brand.currentTextChanged.connect(self.on_brand_changed)
        
    def on_brand_changed(self, brand):
        if brand == "Membrapor":
            self.w_membrapor.show()
            self.w_membrapor_live.show()
            self.chk_plot_temp.setChecked(False)
            self.chk_plot_hum.setChecked(False)
            self.chk_plot_temp.setEnabled(False)
            self.chk_plot_hum.setEnabled(False)
        else:
            self.w_membrapor.hide()
            self.w_membrapor_live.hide()
            self.chk_plot_temp.setEnabled(True)
            self.chk_plot_hum.setEnabled(True)

class PlotCanvas(FigureCanvas):
    def __init__(self, parent=None, width=10, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax_gas_list = []
        self.ax_temp = None
        self.ax_hum = None
        
        super().__init__(self.fig)
        self.setParent(parent)
        self.fig.tight_layout()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Multi-Sensor Data Collection")
        self.resize(1000, 800)
        
        self.settings_file = "settings.json"
        self.logger = DataLogger(None)
        self.is_saving = False
        self.save_start_time = None
        self.max_points = 60
        self.auto_y_scale = True

        # POPUP_AXIS_CONTROLS_PATCH_V7

        # Axis controls live in a separate dialog and cannot resize the dashboard.

        # LEFT_ALIGNED_AXIS_PANEL_PATCH_V6

        # Compact left-aligned axis controls.

        # COMPACT_AXIS_PANEL_PATCH_V5
        # Compact axis layout prevents horizontal window growth.
        # COLLAPSIBLE_AXES_SAFE_RECORDING_PATCH_V4
        # Axis panel can be hidden; recording errors are handled safely.
        # INDIVIDUAL_GAS_AXIS_LIMITS_PATCH_V3
        # Plot-only settings; independent from sensor reading and CSV saving.
        self.manual_axis_limits = {
            'time_window_s': None,
            'gas_by_sensor': {1: None, 2: None, 3: None},
            'temp': None,
            'hum': None,
        }
        self._current_layout_key = None  # tracks when plot structure needs rebuild
        self._lines = {}  # stores Line2D objects keyed by (role, sensor_id)
        
        self.times = deque()
        self.sensor_threads = {1: None, 2: None, 3: None}
        self.latest_data = {1: None, 2: None, 3: None}
        self.expected_serials = {1: None, 2: None, 3: None}
        self.available_ports = {}
        self.adam_callbacks = {1: None, 2: None, 3: None}  # track ADAM subscriptions
        self.adam_raw_mv = {1: deque(maxlen=60), 2: deque(maxlen=60), 3: deque(maxlen=60)}
        
        self.historical_data = {
            1: {'gas': deque(), 'temp': deque(), 'hum': deque()},
            2: {'gas': deque(), 'temp': deque(), 'hum': deque()},
            3: {'gas': deque(), 'temp': deque(), 'hum': deque()}
        }
        self.colors = {1: '#ff7f0e', 2: '#2ca02c', 3: '#9467bd'}
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        self.build_main_tab()
        self.build_settings_tab()
        
        self.load_settings()
        
        self._update_axis_gas_labels()
        self.refresh_all_ports()
        
        for i in range(1, 4):
            self.sensor_configs[i].cmb_port.currentTextChanged.connect(
                lambda text, idx=i: self.on_port_changed(idx)
            )
            # Replot if checkboxes change (needs layout rebuild)
            self.sensor_configs[i].chk_plot_gas.toggled.connect(lambda _: self._force_layout_rebuild())
            self.sensor_configs[i].chk_plot_temp.toggled.connect(lambda _: self._force_layout_rebuild())
            self.sensor_configs[i].chk_plot_hum.toggled.connect(lambda _: self._force_layout_rebuild())
            self.sensor_configs[i].cmb_gas.currentTextChanged.connect(self._on_axis_gas_name_changed)

        
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.plot_tick)
        self.plot_timer.start(1000)

        self.log_timer = QTimer()
        self.log_timer.timeout.connect(self.log_tick)
        self.log_timer.start(1000)
        self.update_log_interval(self.cmb_log_freq.currentText())

    def build_main_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        top_layout = QHBoxLayout()
        
        self.chk_activate = {}
        self.lbl_status = {}
        
        for i in range(1, 4):
            chk = QCheckBox(f"Activate S{i}")
            chk.toggled.connect(lambda checked, idx=i: self.toggle_sensor(idx, checked))
            self.chk_activate[i] = chk
            
            lbl = QLabel("Not Active")
            lbl.setStyleSheet("color: gray; font-weight: bold;")
            self.lbl_status[i] = lbl
            
            top_layout.addWidget(chk)
            top_layout.addWidget(lbl)
            top_layout.addSpacing(15)
            
        top_layout.addStretch()
        
        self.cmb_plot_mode = QComboBox()
        self.cmb_plot_mode.addItems(["Combined Gas Plot", "Separate Gas Plots"])
        self.cmb_plot_mode.currentTextChanged.connect(lambda _: self._force_layout_rebuild())
        top_layout.addWidget(QLabel("Layout:"))
        top_layout.addWidget(self.cmb_plot_mode)
        
        top_layout.addSpacing(20)
        
        self.chk_auto_y = QCheckBox("Auto Y-Scale")
        self.chk_auto_y.setChecked(True)
        self.chk_auto_y.setStyleSheet("font-weight: bold;")
        self.chk_auto_y.toggled.connect(self.toggle_auto_y_scale)
        top_layout.addWidget(self.chk_auto_y)
        
        top_layout.addSpacing(20)
        
        self.chk_save = QCheckBox("Start Saving Data")
        self.chk_save.setStyleSheet("font-weight: bold; color: darkred;")
        self.chk_save.toggled.connect(self.toggle_saving)
        top_layout.addWidget(self.chk_save)
        
        layout.addLayout(top_layout)
        

        
        # Axis controls are kept in a separate dialog. Because the dialog is
        # not part of the dashboard layout, opening it cannot move or crop the
        # graph, recording checkbox, or live readings.
        self.axis_dialog = QDialog(self)
        self.axis_dialog.setWindowTitle("Axis Controls")
        self.axis_dialog.setModal(False)
        self.axis_dialog.setSizeGripEnabled(False)
        self.axis_dialog.setMinimumWidth(355)
        self.axis_dialog.setMaximumWidth(355)

        axis_outer = QVBoxLayout(self.axis_dialog)
        axis_outer.setContentsMargins(10, 10, 10, 10)
        axis_outer.setSpacing(6)

        self.txt_time_window = QLineEdit()
        self.txt_temp_y_min = QLineEdit()
        self.txt_temp_y_max = QLineEdit()
        self.txt_hum_y_min = QLineEdit()
        self.txt_hum_y_max = QLineEdit()
        self.txt_gas_y_min = {}
        self.txt_gas_y_max = {}
        self.lbl_axis_gas_name = {}

        time_row = QHBoxLayout()
        time_row.setSpacing(6)
        time_row.addWidget(QLabel("Visible time (s):"))
        self.txt_time_window.setFixedWidth(72)
        time_row.addWidget(self.txt_time_window)
        time_row.addWidget(QLabel("latest data"))
        time_row.addStretch()
        axis_outer.addLayout(time_row)

        axis_grid = QGridLayout()
        axis_grid.setContentsMargins(0, 0, 0, 0)
        axis_grid.setHorizontalSpacing(6)
        axis_grid.setVerticalSpacing(5)
        axis_grid.addWidget(QLabel("Axis"), 0, 0)
        axis_grid.addWidget(QLabel("Minimum"), 0, 1)
        axis_grid.addWidget(QLabel("Maximum"), 0, 2)

        for sensor_id in range(1, 4):
            row = sensor_id
            gas_label = QLabel(f"S{sensor_id} gas:")
            gas_min = QLineEdit()
            gas_max = QLineEdit()
            gas_min.setFixedWidth(76)
            gas_max.setFixedWidth(76)
            self.lbl_axis_gas_name[sensor_id] = gas_label
            self.txt_gas_y_min[sensor_id] = gas_min
            self.txt_gas_y_max[sensor_id] = gas_max
            axis_grid.addWidget(gas_label, row, 0)
            axis_grid.addWidget(gas_min, row, 1)
            axis_grid.addWidget(gas_max, row, 2)

        self.txt_temp_y_min.setFixedWidth(76)
        self.txt_temp_y_max.setFixedWidth(76)
        axis_grid.addWidget(QLabel("Temperature:"), 4, 0)
        axis_grid.addWidget(self.txt_temp_y_min, 4, 1)
        axis_grid.addWidget(self.txt_temp_y_max, 4, 2)

        self.txt_hum_y_min.setFixedWidth(76)
        self.txt_hum_y_max.setFixedWidth(76)
        axis_grid.addWidget(QLabel("Humidity:"), 5, 0)
        axis_grid.addWidget(self.txt_hum_y_min, 5, 1)
        axis_grid.addWidget(self.txt_hum_y_max, 5, 2)

        all_axis_edits = [
            self.txt_time_window,
            self.txt_temp_y_min, self.txt_temp_y_max,
            self.txt_hum_y_min, self.txt_hum_y_max,
        ]
        for sensor_id in range(1, 4):
            all_axis_edits.extend((
                self.txt_gas_y_min[sensor_id],
                self.txt_gas_y_max[sensor_id],
            ))

        for edit in all_axis_edits:
            edit.setPlaceholderText("Auto")
            edit.returnPressed.connect(self.apply_axis_limits)

        axis_outer.addLayout(axis_grid)

        axis_button_layout = QHBoxLayout()
        self.btn_apply_axis = QPushButton("Apply Axis Limits")
        self.btn_apply_axis.setStyleSheet("font-weight: bold;")
        self.btn_apply_axis.clicked.connect(self.apply_axis_limits)
        axis_button_layout.addWidget(self.btn_apply_axis)

        self.btn_clear_axis = QPushButton("Clear Manual Limits")
        self.btn_clear_axis.clicked.connect(self.clear_axis_limits)
        axis_button_layout.addWidget(self.btn_clear_axis)
        axis_outer.addLayout(axis_button_layout)

        self.lbl_axis_status = QLabel(
            "Each gas uses its own Y-axis in Separate Gas Plots."
        )
        self.lbl_axis_status.setWordWrap(True)
        self.lbl_axis_status.setStyleSheet("color: gray;")
        axis_outer.addWidget(self.lbl_axis_status)

        self.btn_toggle_axis = QPushButton("Axis Controls...")
        self.btn_toggle_axis.setStyleSheet("font-weight: bold;")
        self.btn_toggle_axis.clicked.connect(self._toggle_axis_panel)
        layout.addWidget(self.btn_toggle_axis)


        body_layout = QHBoxLayout()
        
        # Left Side (Plot and Toolbar)
        canvas_layout = QVBoxLayout()
        
        toolbar_layout = QHBoxLayout()
        self.canvas = PlotCanvas(self)
        self.toolbar = NavigationToolbar(self.canvas, self)
        toolbar_layout.addWidget(self.toolbar)
        
        self.btn_reset_view = QPushButton("Reset Plot View")
        self.btn_reset_view.setStyleSheet("font-weight: bold;")
        self.btn_reset_view.clicked.connect(self.reset_plot_view)
        toolbar_layout.addWidget(self.btn_reset_view)
        
        canvas_layout.addLayout(toolbar_layout)
        canvas_layout.addWidget(self.canvas)
        
        body_layout.addLayout(canvas_layout, stretch=5)
        
        # Right Side (Live Values)
        sidebar_layout = QVBoxLayout()
        
        lbl_live_title = QLabel("LIVE READINGS")
        lbl_live_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        lbl_live_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sidebar_layout.addWidget(lbl_live_title)
        
        self.live_labels = {}
        for i in range(1, 4):
            gb = QGroupBox(f"Sensor {i}")
            gb_layout = QVBoxLayout()
            lbl = QLabel("--")
            lbl.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {self.colors[i]}")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.live_labels[i] = lbl
            gb_layout.addWidget(lbl)
            gb.setLayout(gb_layout)
            sidebar_layout.addWidget(gb)
            
        sidebar_layout.addStretch()
        body_layout.addLayout(sidebar_layout, stretch=1)
        
        layout.addLayout(body_layout)
        
        self.cursor = None
        
        self.tabs.addTab(tab, "Main Dashboard")

    def build_settings_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        file_group = QGroupBox("Logging Settings")
        fg_layout = QGridLayout()
        
        fg_layout.addWidget(QLabel("CSV Filename:"), 0, 0)
        self.txt_filename = QLineEdit()
        fg_layout.addWidget(self.txt_filename, 0, 1)
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self.browse_file)
        fg_layout.addWidget(btn_browse, 0, 2)
        
        fg_layout.addWidget(QLabel("Logging Frequency:"), 1, 0)
        self.cmb_log_freq = QComboBox()
        self.cmb_log_freq.addItems(["1 s", "5 s", "10 s", "30 s"])
        self.cmb_log_freq.currentTextChanged.connect(self.update_log_interval)
        fg_layout.addWidget(self.cmb_log_freq, 1, 1)
        
        btn_refresh = QPushButton("Refresh COM Ports")
        btn_refresh.clicked.connect(self.refresh_all_ports)
        fg_layout.addWidget(btn_refresh, 1, 2)
        
        file_group.setLayout(fg_layout)
        layout.addWidget(file_group)
        
        sensors_layout = QHBoxLayout()
        self.sensor_configs = {}
        for i in range(1, 4):
            panel = SensorConfigPanel(i)
            panel.btn_ident.clicked.connect(lambda checked, idx=i: self.flash_led(idx))
            self.sensor_configs[i] = panel
            sensors_layout.addWidget(panel)
        sensors_layout.addWidget(QWidget())
        layout.addLayout(sensors_layout)
        
        layout.addStretch()
        
        btn_save_cfg = QPushButton("Save Config manually")
        btn_save_cfg.clicked.connect(self.save_settings)
        layout.addWidget(btn_save_cfg)
        
        self.tabs.addTab(tab, "Settings")

    def auto_discover_port(self, expected_sn, expected_gas_type, brand):
        GAS_CODES = {"CO": 0x19, "H2": 0x1B, "O2": 0x22}
        target_code = GAS_CODES.get(expected_gas_type)
        
        for port_device, p in self.available_ports.items():
            if expected_sn and p.serial_number == expected_sn:
                return port_device
                
        if brand == "ECSense":
            for port_device, p in self.available_ports.items():
                if p.vid == 0x0403 and p.pid == 0x6001:
                    in_use = False
                    for t in self.sensor_threads.values():
                        if t and t.is_running and t.sensor and t.sensor.port == port_device:
                            in_use = True
                            break
                    if in_use:
                        continue
                        
                    try:
                        import serial
                        with serial.Serial(port_device, 9600, timeout=0.2) as s:
                            s.write(bytes([0xD1]))
                            resp = s.read(9)
                            if len(resp) >= 1 and resp[0] == target_code:
                                return port_device
                    except Exception:
                        pass
        elif brand == "Membrapor":
            # Auto-discovery for Membrapor not implemented yet
            pass
            
        return None

    def flash_led(self, sensor_id):
        panel = self.sensor_configs[sensor_id]
        is_on = panel.btn_ident.isChecked()
        
        if is_on:
            panel.btn_ident.setText("Identify (ON)")
            panel.btn_ident.setStyleSheet("background-color: yellow; font-weight: bold; color: black;")
        else:
            panel.btn_ident.setText("Identify (Off)")
            panel.btn_ident.setStyleSheet("")
            
        if self.sensor_threads[sensor_id] and self.sensor_threads[sensor_id].is_running:
            self.sensor_threads[sensor_id].set_led_state(is_on)
        else:
            sn = self.expected_serials.get(sensor_id)
            if not sn:
                QMessageBox.warning(self, "Warning", "No Serial Number assigned. Please select a valid port first.")
                panel.btn_ident.setChecked(False)
                panel.btn_ident.setText("Identify (Off)")
                panel.btn_ident.setStyleSheet("")
                return
            
            port = self.auto_discover_port(sn, panel.cmb_gas.currentText(), panel.cmb_brand.currentText())
            if port:
                try:
                    s = TB200BSensor(port=port)
                    s.connect()
                    s.set_led(is_on)
                    s.disconnect()
                except Exception as e:
                    QMessageBox.warning(self, "Error", f"Failed to set LED on {port}:\n{e}")
                    panel.btn_ident.setChecked(not is_on) 
                    if not is_on:
                        panel.btn_ident.setText("Identify (ON)")
                        panel.btn_ident.setStyleSheet("background-color: yellow; font-weight: bold; color: black;")
                    else:
                        panel.btn_ident.setText("Identify (Off)")
                        panel.btn_ident.setStyleSheet("")
            else:
                QMessageBox.warning(self, "Warning", f"Could not find sensor '{panel.cmb_gas.currentText()}' on any COM port.")
                panel.btn_ident.setChecked(not is_on)
                if not is_on:
                    panel.btn_ident.setText("Identify (ON)")
                    panel.btn_ident.setStyleSheet("background-color: yellow; font-weight: bold; color: black;")
                else:
                    panel.btn_ident.setText("Identify (Off)")
                    panel.btn_ident.setStyleSheet("")

    def browse_file(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Select CSV File", "", "CSV Files (*.csv);;All Files (*)")
        if fname:
            self.txt_filename.setText(fname)

    def load_settings(self):
        if not os.path.exists(self.settings_file):
            return
        try:
            with open(self.settings_file, 'r') as f:
                data = json.load(f)
                
            if 'csv_filename' in data:
                self.txt_filename.setText(data['csv_filename'])
            if 'log_frequency' in data:
                self.cmb_log_freq.setCurrentText(data['log_frequency'])
            if 'plot_mode' in data:
                self.cmb_plot_mode.setCurrentText(data['plot_mode'])
                
            for i in range(1, 4):
                s_key = str(i)
                if s_key in data:
                    cfg = data[s_key]
                    if 'serial_number' in cfg:
                        self.expected_serials[i] = cfg['serial_number']
                    if 'brand' in cfg:
                        self.sensor_configs[i].cmb_brand.setCurrentText(cfg['brand'])
                    if 'gas_type' in cfg:
                        self.sensor_configs[i].cmb_gas.setCurrentText(cfg['gas_type'])
                    if 'plot_gas' in cfg:
                        self.sensor_configs[i].chk_plot_gas.setChecked(cfg['plot_gas'])
                    if 'plot_temp' in cfg:
                        self.sensor_configs[i].chk_plot_temp.setChecked(cfg['plot_temp'])
                    if 'plot_hum' in cfg:
                        self.sensor_configs[i].chk_plot_hum.setChecked(cfg['plot_hum'])
                    # Membrapor calibration fields
                    if 'adam_model' in cfg:
                        self.sensor_configs[i].cmb_adam_model.setCurrentText(str(cfg['adam_model']))
                    if 'adam_channel' in cfg:
                        self.sensor_configs[i].cmb_adam_ch.setCurrentText(str(cfg['adam_channel']))
                    if 'base_val' in cfg:
                        self.sensor_configs[i].txt_base_val.setText(str(cfg['base_val']))
                    elif 'base_ma' in cfg:
                        self.sensor_configs[i].txt_base_val.setText(str(cfg['base_ma']))
                    if 'max_val' in cfg:
                        self.sensor_configs[i].txt_max_val.setText(str(cfg['max_val']))
                    elif 'max_ma' in cfg:
                        self.sensor_configs[i].txt_max_val.setText(str(cfg['max_ma']))
                    if 'max_gas' in cfg:
                        self.sensor_configs[i].txt_max_gas.setText(str(cfg['max_gas']))
        except Exception as e:
            print(f"Failed to load settings: {e}")

    def save_settings(self):
        data = {
            'csv_filename': self.txt_filename.text(),
            'log_frequency': self.cmb_log_freq.currentText(),
            'plot_mode': self.cmb_plot_mode.currentText(),
        }
        for i in range(1, 4):
            panel = self.sensor_configs[i]
            entry = {
                'serial_number': self.expected_serials[i],
                'brand': panel.cmb_brand.currentText(),
                'gas_type': panel.cmb_gas.currentText(),
                'plot_gas': panel.chk_plot_gas.isChecked(),
                'plot_temp': panel.chk_plot_temp.isChecked(),
                'plot_hum': panel.chk_plot_hum.isChecked()
            }
            if panel.cmb_brand.currentText() == "Membrapor":
                entry['adam_model'] = panel.cmb_adam_model.currentText()
                entry['adam_channel'] = int(panel.cmb_adam_ch.currentText())
                try:
                    entry['base_val'] = float(panel.txt_base_val.text())
                    entry['max_val'] = float(panel.txt_max_val.text())
                    entry['max_gas'] = float(panel.txt_max_gas.text())
                except ValueError:
                    entry['base_val'] = 0.0
                    entry['max_val'] = 30.0
                    entry['max_gas'] = 100.0
            data[str(i)] = entry
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Failed to save settings: {e}")

    def toggle_saving(self, checked):
        """Start/stop CSV logging without allowing a file error to close the GUI."""
        if not checked:
            self.save_start_time = None
            self.is_saving = False
            self._force_layout_rebuild()
            return

        try:
            fname = self.txt_filename.text().strip()
            if not fname:
                QMessageBox.warning(
                    self,
                    "Recording Not Started",
                    "Please select a CSV filename in the Settings tab."
                )
                self.chk_save.blockSignals(True)
                self.chk_save.setChecked(False)
                self.chk_save.blockSignals(False)
                return

            # Normalize the path and make its parent folder when necessary.
            fname = os.path.abspath(os.path.expanduser(fname))
            parent_folder = os.path.dirname(fname)
            if parent_folder and not os.path.isdir(parent_folder):
                os.makedirs(parent_folder, exist_ok=True)
            self.txt_filename.setText(fname)

            no_sensor_active = not any(
                self.chk_activate[sensor_id].isChecked()
                for sensor_id in range(1, 4)
            )
            if no_sensor_active:
                QMessageBox.information(
                    self,
                    "No Sensors Active",
                    "Recording can still start, but NaN values will be written "
                    "until sensors are activated and provide readings."
                )

            if os.path.exists(fname):
                QMessageBox.information(
                    self,
                    "Appending Data",
                    f"The file '{fname}' already exists.\nData will be appended to it."
                )

            # Open/create the file before clearing the plot history. Any file/path
            # problem is caught below and shown as a message instead of closing Qt.
            self.logger.set_filename(fname)
            self.logger.start_session()

            self.times.clear()
            for sensor_id in range(1, 4):
                self.historical_data[sensor_id]['gas'].clear()
                self.historical_data[sensor_id]['temp'].clear()
                self.historical_data[sensor_id]['hum'].clear()

            self.save_start_time = self.logger.start_time
            self.is_saving = True
            self._force_layout_rebuild()

        except Exception as exc:
            self.save_start_time = None
            self.is_saving = False
            self.chk_save.blockSignals(True)
            self.chk_save.setChecked(False)
            self.chk_save.blockSignals(False)
            print(f"Failed to start recording: {type(exc).__name__}: {exc}")
            QMessageBox.critical(
                self,
                "Recording Error",
                "Recording could not start, but the program will remain open.\n\n"
                f"{type(exc).__name__}: {exc}\n\n"
                "Choose another CSV location in the Settings tab and try again."
            )

    def update_log_interval(self, text):
        try:
            val = int(text.split()[0])
            self.log_timer.setInterval(val * 1000)
        except:
            pass

    def refresh_all_ports(self):
        self.available_ports = {p.device: p for p in serial.tools.list_ports.comports()}
        
        for i in range(1, 4):
            cfg = self.sensor_configs[i]
            curr_port = cfg.cmb_port.currentText()
            expected_sn = self.expected_serials.get(i, None)
            expected_gas = cfg.cmb_gas.currentText()
            expected_brand = cfg.cmb_brand.currentText()
            
            cfg.cmb_port.blockSignals(True)
            cfg.cmb_port.clear()
            cfg.cmb_port.addItem("None")
            
            for port_device in self.available_ports.keys():
                cfg.cmb_port.addItem(port_device)
                
            target_port = self.auto_discover_port(expected_sn, expected_gas, expected_brand)
            
            if not target_port:
                if expected_sn:
                    missing_text = f"Disconnected (SN: {expected_sn})"
                    cfg.cmb_port.addItem(missing_text)
                    target_port = missing_text
                elif curr_port in self.available_ports:
                    target_port = curr_port
                else:
                    target_port = "None"
                    
            cfg.cmb_port.setCurrentText(target_port)
            cfg.cmb_port.blockSignals(False)
            
            self.on_port_changed(i)

    def on_port_changed(self, sensor_id):
        port_name = self.sensor_configs[sensor_id].cmb_port.currentText()
        panel = self.sensor_configs[sensor_id]
        
        panel.lbl_info.setText("Sensor Info: N/A")
        
        if port_name in self.available_ports:
            sn = self.available_ports[port_name].serial_number
            if sn:
                panel.lbl_serial.setText(f"SN: {sn}")
                self.expected_serials[sensor_id] = sn
            else:
                panel.lbl_serial.setText("SN: Unknown")
                self.expected_serials[sensor_id] = None
                
            if not (self.sensor_threads[sensor_id] and self.sensor_threads[sensor_id].is_running):
                if panel.cmb_brand.currentText() == "ECSense":
                    try:
                        import serial
                        with serial.Serial(port_name, 9600, timeout=0.2) as s:
                            s.write(bytes([0xD1]))
                            resp = s.read(9)
                            if len(resp) == 9:
                                range_val = (resp[1] << 8) | resp[2]
                                unit = "ppb" if resp[3] == 0x04 else "ppm"
                                gas_map = {0x19: "CO", 0x1B: "H2", 0x22: "O2"}
                                gas_name = gas_map.get(resp[0], "Unknown")
                                panel.lbl_info.setText(f"Info: {range_val} {unit} ({gas_name})")
                    except Exception:
                        pass
                elif panel.cmb_brand.currentText() == "Membrapor":
                    panel.lbl_info.setText("Info: Membrapor Sensor")
                    
        elif port_name.startswith("Disconnected"):
            sn = self.expected_serials[sensor_id]
            if sn:
                panel.lbl_serial.setText(f"SN: {sn} (Offline)")
        else:
            panel.lbl_serial.setText("SN: N/A")
            self.expected_serials[sensor_id] = None
            
        self.save_settings()

    def toggle_sensor(self, sensor_id, checked):
        panel = self.sensor_configs[sensor_id]
        brand = panel.cmb_brand.currentText()
        
        if checked:
            if brand == "ECSense":
                sn = self.expected_serials.get(sensor_id)
                if not sn:
                    self.chk_activate[sensor_id].blockSignals(True)
                    self.chk_activate[sensor_id].setChecked(False)
                    self.chk_activate[sensor_id].blockSignals(False)
                    QMessageBox.warning(self, "Warning", f"No valid Serial Number assigned for Sensor {sensor_id}.")
                    return
                    
                gas_type = panel.cmb_gas.currentText()
                
                thread = SensorThread(serial_number=sn, baudrate=9600, gas_type=gas_type, brand=brand)
                thread.data_received.connect(lambda data, idx=sensor_id: self.on_data_received(idx, data))
                thread.status_changed.connect(lambda status, idx=sensor_id: self.on_status_changed(idx, status))
                thread.sensor_info_received.connect(lambda info, idx=sensor_id: self.on_sensor_info(idx, info))
                thread.error_occurred.connect(lambda err, idx=sensor_id: print(f"Sensor {idx} Error: {err}"))
                
                self.sensor_threads[sensor_id] = thread
                thread.start()
                
            elif brand == "Membrapor":
                port_name = panel.cmb_port.currentText()
                if port_name == "None" or port_name not in self.available_ports:
                    self.chk_activate[sensor_id].blockSignals(True)
                    self.chk_activate[sensor_id].setChecked(False)
                    self.chk_activate[sensor_id].blockSignals(False)
                    QMessageBox.warning(self, "Warning", f"Please select a valid COM port for Sensor {sensor_id} (ADAM module).")
                    return
                
                adam_ch = int(panel.cmb_adam_ch.currentText())
                try:
                    base_val = float(panel.txt_base_val.text())
                    max_val = float(panel.txt_max_val.text())
                    max_gas = float(panel.txt_max_gas.text())
                except ValueError:
                    QMessageBox.warning(self, "Warning", "Invalid calibration values. Please enter valid numbers.")
                    self.chk_activate[sensor_id].blockSignals(True)
                    self.chk_activate[sensor_id].setChecked(False)
                    self.chk_activate[sensor_id].blockSignals(False)
                    return
                
                def make_adam_callback(sid, ch, b_val, m_val, m_gas):
                    def cb(vals):
                        raw_val = vals[ch]
                        self.adam_raw_mv[sid].append(raw_val)
                        span = m_val - b_val
                        gas_val = (raw_val - b_val) * (m_gas / span) if span != 0 else 0.0
                        self.latest_data[sid] = {
                            'gas_ppb': gas_val,
                            'gas_ug_m3': 0.0,
                            'temperature_c': np.nan,
                            'humidity_rh': np.nan
                        }
                    return cb
                
                adam_model = panel.cmb_adam_model.currentText()
                callback = make_adam_callback(sensor_id, adam_ch, base_val, max_val, max_gas)
                self.adam_callbacks[sensor_id] = (port_name, callback)
                adam_manager.subscribe(port_name, callback, model=adam_model)
                self.on_status_changed(sensor_id, "Connected")
                panel.lbl_info.setText(f"Info: {adam_model} Ch{adam_ch} | {base_val}-{max_val} mV → {max_gas} ppm {panel.cmb_gas.currentText()}")
        else:
            # Deactivate
            if brand == "Membrapor" or self.adam_callbacks.get(sensor_id):
                if self.adam_callbacks.get(sensor_id):
                    port, cb = self.adam_callbacks[sensor_id]
                    adam_manager.unsubscribe(port, cb)
                    self.adam_callbacks[sensor_id] = None
                    self.adam_raw_mv[sensor_id].clear()
            if self.sensor_threads[sensor_id]:
                self.sensor_threads[sensor_id].stop()
                self.sensor_threads[sensor_id] = None
            self.latest_data[sensor_id] = None
            self.lbl_status[sensor_id].setText("Not Active")
            self.lbl_status[sensor_id].setStyleSheet("color: gray; font-weight: bold;")

    def on_sensor_info(self, sensor_id, info):
        self.sensor_configs[sensor_id].lbl_info.setText(f"Info: {info}")

    def on_data_received(self, sensor_id, data):
        self.latest_data[sensor_id] = data

    def on_status_changed(self, sensor_id, status):
        color = "black"
        if status == "Connected":
            color = "green"
        elif status == "Error":
            color = "red"
        elif status == "Disconnected":
            color = "gray"
        elif status == "Connecting":
            color = "orange"
            
        self.lbl_status[sensor_id].setText(status)
        self.lbl_status[sensor_id].setStyleSheet(f"color: {color}; font-weight: bold;")

    def log_tick(self):
        if not self.is_saving:
            return

        try:
            s1 = self.latest_data[1]
            s2 = self.latest_data[2]
            s3 = self.latest_data[3]
            self.logger.log(s1, s2, s3)
        except Exception as exc:
            # PyQt can terminate on an uncaught exception inside a timer slot.
            # Stop recording safely and keep the main window running.
            self.is_saving = False
            self.save_start_time = None
            self.chk_save.blockSignals(True)
            self.chk_save.setChecked(False)
            self.chk_save.blockSignals(False)
            print(f"Recording stopped: {type(exc).__name__}: {exc}")
            QMessageBox.critical(
                self,
                "Recording Stopped",
                "An error occurred while writing the CSV file. Recording was "
                "stopped, but the program remains open.\n\n"
                f"{type(exc).__name__}: {exc}"
            )
            self._force_layout_rebuild()

    def plot_tick(self):
        now = datetime.now()
        self.times.append(now)
        
        for i in range(1, 4):
            data = self.latest_data[i]
            
            # Update Live Value Sidebar
            if data is None:
                self.live_labels[i].setText("--")
            else:
                gas_val = data.get('gas_ppb', np.nan)
                temp_val = data.get('temperature_c', np.nan)
                hum_val = data.get('humidity_rh', np.nan)
                gas_name = self.sensor_configs[i].cmb_gas.currentText()
                
                text = f"{gas_name}: {gas_val:.1f} ppm"
                if not np.isnan(temp_val):
                    text += f"\nTemp: {temp_val:.1f} °C"
                if not np.isnan(hum_val):
                    text += f"\nHum: {hum_val:.1f} %"
                self.live_labels[i].setText(text)
                
            if data is None:
                self.historical_data[i]['gas'].append(np.nan)
                self.historical_data[i]['temp'].append(np.nan)
                self.historical_data[i]['hum'].append(np.nan)
            else:
                self.historical_data[i]['gas'].append(data.get('gas_ppb', np.nan))
                self.historical_data[i]['temp'].append(data.get('temperature_c', np.nan))
                self.historical_data[i]['hum'].append(data.get('humidity_rh', np.nan))
                
        # Update Membrapor calibration displays
        for i in range(1, 4):
            panel = self.sensor_configs[i]
            if panel.cmb_brand.currentText() == "Membrapor" and len(self.adam_raw_mv[i]) > 0:
                latest = self.adam_raw_mv[i][-1]
                panel.lbl_live_mv.setText(f"Live: {latest:.3f} mV")
                arr = np.array(self.adam_raw_mv[i])
                panel.lbl_avg_mv.setText(f"60s Avg: {np.mean(arr):.3f} mV")
                if len(arr) >= 2:
                    panel.lbl_std_mv.setText(f"60s Std: {np.std(arr):.4f} mV")
                else:
                    panel.lbl_std_mv.setText("60s Std: -- mV")
            else:
                panel.lbl_live_mv.setText("Live: -- mV")
                panel.lbl_avg_mv.setText("60s Avg: -- mV")
                panel.lbl_std_mv.setText("60s Std: -- mV")
        
        self._update_data_only()

    def _compute_layout_key(self):
        """Return a hashable key representing the current plot structure."""
        mode = self.cmb_plot_mode.currentText()
        gas_checked = tuple(self.sensor_configs[i].chk_plot_gas.isChecked() for i in range(1, 4))
        temp_checked = tuple(self.sensor_configs[i].chk_plot_temp.isChecked() for i in range(1, 4))
        hum_checked = tuple(self.sensor_configs[i].chk_plot_hum.isChecked() for i in range(1, 4))
        has_elapsed = self.save_start_time is not None
        return (mode, gas_checked, temp_checked, hum_checked, has_elapsed)

    def _force_layout_rebuild(self):
        """Invalidate layout and rebuild immediately."""
        self._current_layout_key = None
        self.update_plot()

    def _toggle_axis_panel(self, _checked=False):
        """Open or hide the independent axis-controls dialog."""
        if not hasattr(self, 'axis_dialog'):
            return

        if self.axis_dialog.isVisible():
            self.axis_dialog.hide()
            return

        self.axis_dialog.adjustSize()
        self.axis_dialog.show()
        self.axis_dialog.raise_()
        self.axis_dialog.activateWindow()

    def _update_axis_gas_labels(self):
        if not hasattr(self, 'lbl_axis_gas_name'):
            return
        for sensor_id in range(1, 4):
            gas_name = "Gas"
            if hasattr(self, 'sensor_configs') and sensor_id in self.sensor_configs:
                gas_name = self.sensor_configs[sensor_id].cmb_gas.currentText() or "Gas"
            self.lbl_axis_gas_name[sensor_id].setText(
                f"S{sensor_id} {gas_name}:"
            )

    def _on_axis_gas_name_changed(self, _text):
        self._update_axis_gas_labels()
        self._force_layout_rebuild()

    def _parse_axis_range(self, minimum_edit, maximum_edit, label):
        minimum_text = minimum_edit.text().strip()
        maximum_text = maximum_edit.text().strip()

        if not minimum_text and not maximum_text:
            return None
        if not minimum_text or not maximum_text:
            raise ValueError(f"{label}: enter both minimum and maximum, or leave both blank.")

        try:
            minimum = float(minimum_text)
            maximum = float(maximum_text)
        except ValueError as exc:
            raise ValueError(f"{label}: use numbers only.") from exc

        if not np.isfinite(minimum) or not np.isfinite(maximum):
            raise ValueError(f"{label}: values must be finite numbers.")
        if minimum >= maximum:
            raise ValueError(f"{label}: minimum must be smaller than maximum.")
        return minimum, maximum

    def apply_axis_limits(self):
        try:
            window_text = self.txt_time_window.text().strip()
            if window_text:
                time_window_s = float(window_text)
                if not np.isfinite(time_window_s) or time_window_s <= 0:
                    raise ValueError("Visible time must be greater than zero.")
            else:
                time_window_s = None

            gas_limits = {}
            for sensor_id in range(1, 4):
                gas_name = self.sensor_configs[sensor_id].cmb_gas.currentText()
                gas_limits[sensor_id] = self._parse_axis_range(
                    self.txt_gas_y_min[sensor_id],
                    self.txt_gas_y_max[sensor_id],
                    f"S{sensor_id} {gas_name} axis",
                )

            temp_limits = self._parse_axis_range(
                self.txt_temp_y_min, self.txt_temp_y_max, "Temperature axis"
            )
            hum_limits = self._parse_axis_range(
                self.txt_hum_y_min, self.txt_hum_y_max, "Humidity axis"
            )
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid Axis Limits", str(exc))
            return

        self.manual_axis_limits = {
            'time_window_s': time_window_s,
            'gas_by_sensor': gas_limits,
            'temp': temp_limits,
            'hum': hum_limits,
        }

        has_manual_y = (
            any(value is not None for value in gas_limits.values())
            or temp_limits is not None
            or hum_limits is not None
        )
        if has_manual_y:
            self.chk_auto_y.blockSignals(True)
            self.chk_auto_y.setChecked(False)
            self.chk_auto_y.blockSignals(False)
            self.auto_y_scale = False

        active_gases = [
            sensor_id for sensor_id in range(1, 4)
            if self.sensor_configs[sensor_id].chk_plot_gas.isChecked()
        ]
        manual_active_gases = [
            sensor_id for sensor_id in active_gases
            if gas_limits.get(sensor_id) is not None
        ]

        switched_layout = False
        if (
            len(active_gases) > 1
            and manual_active_gases
            and self.cmb_plot_mode.currentText() != "Separate Gas Plots"
        ):
            self.cmb_plot_mode.setCurrentText("Separate Gas Plots")
            switched_layout = True

        if switched_layout:
            self.lbl_axis_status.setText(
                "Axis limits applied. Layout changed to Separate Gas Plots so each gas has its own Y-axis."
            )
        else:
            self.lbl_axis_status.setText("Independent axis limits applied.")
        self.lbl_axis_status.setStyleSheet("color: darkgreen; font-weight: bold;")

        if not switched_layout:
            self._update_data_only()

    def clear_axis_limits(self, redraw=True):
        self.manual_axis_limits = {
            'time_window_s': None,
            'gas_by_sensor': {1: None, 2: None, 3: None},
            'temp': None,
            'hum': None,
        }

        edits = [
            self.txt_time_window,
            self.txt_temp_y_min, self.txt_temp_y_max,
            self.txt_hum_y_min, self.txt_hum_y_max,
        ]
        for sensor_id in range(1, 4):
            edits.extend((
                self.txt_gas_y_min[sensor_id],
                self.txt_gas_y_max[sensor_id],
            ))
        for edit in edits:
            edit.clear()

        self.chk_auto_y.blockSignals(True)
        self.chk_auto_y.setChecked(True)
        self.chk_auto_y.blockSignals(False)
        self.auto_y_scale = True
        self.lbl_axis_status.setText("Automatic plot limits restored.")
        self.lbl_axis_status.setStyleSheet("color: gray;")

        if redraw:
            self._update_data_only()

    def _set_following_x_limit(self, axis, times_list):
        window_s = self.manual_axis_limits.get('time_window_s')
        if window_s is not None and times_list:
            right = times_list[-1]
            left = right - timedelta(seconds=window_s)
            axis.set_xlim(left, right)
        else:
            axis.autoscale_view(scalex=True, scaley=False)

    def toggle_auto_y_scale(self, checked):
        self.auto_y_scale = checked
        if checked:
            # Re-autoscale immediately
            for ax, sensors in self.canvas.ax_gas_list:
                max_val = 0.01
                for i in sensors:
                    valid_data = [v for v in self.historical_data[i]['gas'] if not np.isnan(v)]
                    if valid_data:
                        max_val = max(max_val, max(valid_data))
                ax.set_ylim(0, max_val * 1.1)
            if self.canvas.ax_temp:
                self.canvas.ax_temp.relim()
                self.canvas.ax_temp.autoscale_view(scalex=False, scaley=True)
            if self.canvas.ax_hum:
                self.canvas.ax_hum.relim()
                self.canvas.ax_hum.autoscale_view(scalex=False, scaley=True)
            self.canvas.draw()

    def reset_plot_view(self):
        self.clear_axis_limits(redraw=False)

        all_axes = [ax for ax, _ in self.canvas.ax_gas_list]
        if self.canvas.ax_temp:
            all_axes.append(self.canvas.ax_temp)
        if self.canvas.ax_hum:
            all_axes.append(self.canvas.ax_hum)

        for axis in all_axes:
            axis.relim()
            axis.autoscale(enable=True, axis='both', tight=False)

        for axis, _ in self.canvas.ax_gas_list:
            axis.set_ylim(bottom=0)

        self.canvas.draw()

    def _rebuild_layout(self):
        """Clear figure and recreate axes structure. Only called when layout changes."""
        self.canvas.fig.clear()
        self.canvas.ax_gas_list = []
        self.canvas.ax_temp = None
        self.canvas.ax_hum = None
        self._lines = {}
        self.cursor = None

        mode = self.cmb_plot_mode.currentText()
        any_gas = any(cfg.chk_plot_gas.isChecked() for cfg in self.sensor_configs.values())
        any_temp = any(cfg.chk_plot_temp.isChecked() for cfg in self.sensor_configs.values())
        any_hum = any(cfg.chk_plot_hum.isChecked() for cfg in self.sensor_configs.values())

        if not any_gas and not any_temp and not any_hum:
            self.canvas.draw()
            return

        checked_gases = [i for i in range(1, 4) if self.sensor_configs[i].chk_plot_gas.isChecked()]
        num_gas_rows = 1
        if mode == "Separate Gas Plots" and any_gas:
            num_gas_rows = max(1, len(checked_gases))

        bottom_row = 1 if (any_temp or any_hum) else 0
        total_rows = (num_gas_rows if any_gas else 0) + bottom_row

        gs = gridspec.GridSpec(total_rows, 2, figure=self.canvas.fig)
        current_row = 0
        shared_x = None

        # Allocate Gas Axes
        if any_gas:
            if mode == "Combined Gas Plot":
                ax = self.canvas.fig.add_subplot(gs[current_row, :])
                self.canvas.ax_gas_list.append((ax, checked_gases))
                shared_x = ax
                current_row += 1
            else:
                for idx in checked_gases:
                    if shared_x is None:
                        ax = self.canvas.fig.add_subplot(gs[current_row, :])
                        shared_x = ax
                    else:
                        ax = self.canvas.fig.add_subplot(gs[current_row, :], sharex=shared_x)
                    self.canvas.ax_gas_list.append((ax, [idx]))
                    current_row += 1

        # Allocate Temp/Hum Axes
        if any_temp and any_hum:
            ax_t = self.canvas.fig.add_subplot(gs[current_row, 0], sharex=shared_x)
            ax_h = self.canvas.fig.add_subplot(gs[current_row, 1], sharex=shared_x)
            self.canvas.ax_temp = ax_t
            self.canvas.ax_hum = ax_h
        elif any_temp:
            ax_t = self.canvas.fig.add_subplot(gs[current_row, :], sharex=shared_x)
            self.canvas.ax_temp = ax_t
        elif any_hum:
            ax_h = self.canvas.fig.add_subplot(gs[current_row, :], sharex=shared_x)
            self.canvas.ax_hum = ax_h

        # Setup secondary elapsed-time axis
        from matplotlib.ticker import FuncFormatter

        def forward(x):
            if not self.save_start_time: return x
            t0 = mdates.date2num(self.save_start_time)
            return (x - t0) * 24.0 * 3600.0

        def inverse(x):
            if not self.save_start_time: return x
            t0 = mdates.date2num(self.save_start_time)
            return x / (24.0 * 3600.0) + t0

        def format_elapsed(x, pos):
            if x < 0: return ""
            hrs = int(x // 3600)
            mins = int((x % 3600) // 60)
            secs = int(x % 60)
            return f"{hrs:02d}:{mins:02d}:{secs:02d}"

        if self.canvas.ax_gas_list and self.save_start_time:
            top_ax = self.canvas.ax_gas_list[0][0]
            secax = top_ax.secondary_xaxis('top', functions=(forward, inverse))
            secax.xaxis.set_major_formatter(FuncFormatter(format_elapsed))
            secax.set_xlabel('Elapsed Time')

        # Create empty Line2D objects for each data series
        for ax_idx, (ax, sensors) in enumerate(self.canvas.ax_gas_list):
            ax.set_ylabel('Gas (ppm)')
            ax.grid(True, linestyle='--', alpha=0.7)
            for i in sensors:
                cfg = self.sensor_configs[i]
                line, = ax.plot([], [], label=f'S{i} ({cfg.cmb_gas.currentText()})', color=self.colors[i])
                self._lines[('gas', i)] = line
            ax.legend(loc='upper left', fontsize='small')

        if self.canvas.ax_temp:
            self.canvas.ax_temp.set_ylabel('Temp (°C)')
            self.canvas.ax_temp.grid(True, linestyle='--', alpha=0.7)
            for i in range(1, 4):
                if self.sensor_configs[i].chk_plot_temp.isChecked():
                    line, = self.canvas.ax_temp.plot([], [], label=f'S{i}', color=self.colors[i])
                    self._lines[('temp', i)] = line
            self.canvas.ax_temp.legend(loc='upper left', fontsize='small')

        if self.canvas.ax_hum:
            self.canvas.ax_hum.set_ylabel('Humidity (%)')
            self.canvas.ax_hum.grid(True, linestyle='--', alpha=0.7)
            for i in range(1, 4):
                if self.sensor_configs[i].chk_plot_hum.isChecked():
                    line, = self.canvas.ax_hum.plot([], [], label=f'S{i}', color=self.colors[i])
                    self._lines[('hum', i)] = line
            self.canvas.ax_hum.legend(loc='upper left', fontsize='small')

        # Format X-Axis Time and Hide Upper Ticks
        for i, (ax, _) in enumerate(self.canvas.ax_gas_list):
            if (any_temp or any_hum) or i < len(self.canvas.ax_gas_list) - 1:
                ax.tick_params(labelbottom=False)
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        if self.canvas.ax_temp:
            self.canvas.ax_temp.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        if self.canvas.ax_hum:
            self.canvas.ax_hum.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))

        self.canvas.fig.autofmt_xdate(rotation=45)
        self.canvas.fig.tight_layout()

        # Initialize Interactive Cursor
        all_axes = [ax for ax, _ in self.canvas.ax_gas_list]
        if self.canvas.ax_temp: all_axes.append(self.canvas.ax_temp)
        if self.canvas.ax_hum: all_axes.append(self.canvas.ax_hum)

        if all_axes:
            self.cursor = MultiCursor(self.canvas.fig.canvas, all_axes, color='gray', lw=1, horizOn=True, vertOn=True)

    def _update_data_only(self):
        """Update plotted data and keep independent typed limits active."""
        times_list = list(self.times)
        gas_limits_by_sensor = self.manual_axis_limits.get(
            'gas_by_sensor', {1: None, 2: None, 3: None}
        )

        # Gas plots
        for axis, sensors in self.canvas.ax_gas_list:
            maximum_value = 0.01
            for sensor_id in sensors:
                data_list = list(self.historical_data[sensor_id]['gas'])
                key = ('gas', sensor_id)
                if key in self._lines:
                    self._lines[key].set_data(times_list, data_list)
                valid = [value for value in data_list if not np.isnan(value)]
                if valid:
                    maximum_value = max(maximum_value, max(valid))

            axis.relim()
            self._set_following_x_limit(axis, times_list)

            manual_ranges = [
                gas_limits_by_sensor.get(sensor_id)
                for sensor_id in sensors
                if gas_limits_by_sensor.get(sensor_id) is not None
            ]
            if len(sensors) == 1 and manual_ranges:
                axis.set_ylim(*manual_ranges[0])
            elif manual_ranges:
                # Combined mode has one shared physical Y-axis. Use an envelope
                # if the user manually switches back after applying ranges.
                axis.set_ylim(
                    min(value[0] for value in manual_ranges),
                    max(value[1] for value in manual_ranges),
                )
            elif self.auto_y_scale:
                axis.set_ylim(0, maximum_value * 1.1)

        # Temperature plot
        if self.canvas.ax_temp:
            for sensor_id in range(1, 4):
                key = ('temp', sensor_id)
                if key in self._lines:
                    self._lines[key].set_data(
                        times_list, list(self.historical_data[sensor_id]['temp'])
                    )
            self.canvas.ax_temp.relim()
            self._set_following_x_limit(self.canvas.ax_temp, times_list)
            temp_limits = self.manual_axis_limits.get('temp')
            if temp_limits is not None:
                self.canvas.ax_temp.set_ylim(*temp_limits)
            elif self.auto_y_scale:
                self.canvas.ax_temp.autoscale_view(scalex=False, scaley=True)

        # Humidity plot
        if self.canvas.ax_hum:
            for sensor_id in range(1, 4):
                key = ('hum', sensor_id)
                if key in self._lines:
                    self._lines[key].set_data(
                        times_list, list(self.historical_data[sensor_id]['hum'])
                    )
            self.canvas.ax_hum.relim()
            self._set_following_x_limit(self.canvas.ax_hum, times_list)
            hum_limits = self.manual_axis_limits.get('hum')
            if hum_limits is not None:
                self.canvas.ax_hum.set_ylim(*hum_limits)
            elif self.auto_y_scale:
                self.canvas.ax_hum.autoscale_view(scalex=False, scaley=True)

        self.canvas.draw()

    def update_plot(self):
        """Check if layout needs rebuild, then update data."""
        layout_key = self._compute_layout_key()
        if layout_key != self._current_layout_key:
            self._rebuild_layout()
            self._current_layout_key = layout_key
        self._update_data_only()

    def closeEvent(self, event):
        self.save_settings()
        for i in range(1, 4):
            if self.sensor_threads[i]:
                self.sensor_threads[i].stop()
            if self.adam_callbacks.get(i):
                port, cb = self.adam_callbacks[i]
                adam_manager.unsubscribe(port, cb)
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
