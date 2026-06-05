import csv
import os
import math
from datetime import datetime

class DataLogger:
    def __init__(self, filename="sensor_data.csv"):
        self.filename = None
        self.start_time = None
        self.headers = ["timestamp", "passed_secs"]
        for i in range(1, 4):
            self.headers.extend([
                f"S{i}_gas_ppb", 
                f"S{i}_gas_ug_m3", 
                f"S{i}_temperature_c", 
                f"S{i}_humidity_rh"
            ])
            
        if filename:
            self.set_filename(filename)

    def set_filename(self, filename):
        self.filename = filename
        self._initialize_file()

    def start_session(self):
        """Records the start time of the logging session."""
        self.start_time = datetime.now()

    def _initialize_file(self):
        """Creates the file with headers if it doesn't exist."""
        if not self.filename:
            return
        if not os.path.exists(self.filename):
            with open(self.filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writeheader()

    def log(self, s1_data, s2_data, s3_data):
        """
        Appends a new reading to the CSV file.
        sX_data should be a dict with keys: 'gas_ppb', 'gas_ug_m3', 'temperature_c', 'humidity_rh'
        If a sensor is disconnected or errored, its data should be None, and NaN will be written.
        """
        now = datetime.now()
        passed_secs = (now - self.start_time).total_seconds() if self.start_time else 0.0
        row = {
            'timestamp': now.isoformat(),
            'passed_secs': f"{passed_secs:.1f}"
        }
        
        sensor_data_list = [s1_data, s2_data, s3_data]
        
        for i, data in enumerate(sensor_data_list, start=1):
            if data is None:
                row[f"S{i}_gas_ppb"] = "NaN"
                row[f"S{i}_gas_ug_m3"] = "NaN"
                row[f"S{i}_temperature_c"] = "NaN"
                row[f"S{i}_humidity_rh"] = "NaN"
            else:
                row[f"S{i}_gas_ppb"] = data.get('gas_ppb', "NaN")
                row[f"S{i}_gas_ug_m3"] = data.get('gas_ug_m3', "NaN")
                row[f"S{i}_temperature_c"] = data.get('temperature_c', "NaN")
                row[f"S{i}_humidity_rh"] = data.get('humidity_rh', "NaN")
                
        try:
            with open(self.filename, 'a', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writerow(row)
        except Exception as e:
            print(f"Error logging data: {e}")
