
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from collections import deque
from datetime import datetime
import matplotlib.dates as mdates

class LivePlotter:
    def __init__(self, max_points=50, update_interval=1000, data_provider=None):
        self.max_points = max_points
        self.times = deque(maxlen=max_points)
        self.gas = deque(maxlen=max_points)
        self.temp = deque(maxlen=max_points)
        self.hum = deque(maxlen=max_points)
        
        self.data_provider = data_provider
        self.update_interval = update_interval
        
        # Setup plot
        plt.style.use('fivethirtyeight')
        self.fig, (self.ax1, self.ax2, self.ax3) = plt.subplots(3, 1, figsize=(10, 8), sharex=True)
        self.fig.suptitle('TB200B Sensor Data')

    def _update(self, frame):
        # Fetch new data
        if self.data_provider:
            new_data = self.data_provider()
            if new_data:
                now = datetime.now()
                self.times.append(now)
                self.gas.append(new_data.get('gas_ug_m3', 0))
                self.temp.append(new_data.get('temperature_c', 0))
                self.hum.append(new_data.get('humidity_rh', 0))

        # Clear and plotter
        self.ax1.clear()
        self.ax2.clear()
        self.ax3.clear()
        
        # Plot Gas
        self.ax1.plot(self.times, self.gas, label='Gas (ug/m3)', color='#ff7f0e')
        self.ax1.legend(loc='upper left')
        self.ax1.set_ylabel('ug/m3')

        # Plot Temp
        self.ax2.plot(self.times, self.temp, label='Temperature (°C)', color='#d62728')
        self.ax2.legend(loc='upper left')
        self.ax2.set_ylabel('°C')

        # Plot Humidity
        self.ax3.plot(self.times, self.hum, label='Humidity (%)', color='#1f77b4')
        self.ax3.legend(loc='upper left')
        self.ax3.set_ylabel('%')
        self.ax3.set_xlabel('Time')

        # Format X Axis
        self.ax3.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        plt.setp(self.ax3.xaxis.get_majorticklabels(), rotation=45)

    def start(self):
        """Starts the animation loop. Blocking call."""
        # Note: we need to keep a reference to 'ani' otherwise it gets garbage collected
        self.ani = FuncAnimation(self.fig, self._update, interval=self.update_interval, cache_frame_data=False)
        plt.show()
