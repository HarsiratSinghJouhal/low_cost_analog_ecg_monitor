import time
import serial
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import CheckButtons
from scipy.signal import iirnotch, butter, lfilter, lfilter_zi, savgol_filter, medfilt
from collections import deque

# --- CONFIGURATION ---
SERIAL_PORT = 'COM4'  # Verified CH340 port
BAUD_RATE = 115200
FS = 500.0            # Sampling frequency (Hz)
WINDOW_SEC = 4        # 4 seconds visible on screen
BUF_LEN = int(FS * WINDOW_SEC)

# Fixed Y-axis limits when Auto-Scale is OFF
FIXED_RAW_LIM = (0, 1024)
FIXED_FILT_LIM = (-60, 60)

# --- FILTER DESIGN ---
# 1. 50 Hz Digital Notch Filter (Fundamental + 100 Hz 2nd Harmonic)
b_notch, a_notch = iirnotch(50.0, 25.0, FS)
zi_notch = lfilter_zi(b_notch, a_notch) * 512.0

b_notch2, a_notch2 = iirnotch(100.0, 25.0, FS)
zi_notch2 = lfilter_zi(b_notch2, a_notch2) * 512.0

# 2. 1.5 Hz High-Pass Filter (Kills coin-pressure baseline drift)
b_hpf, a_hpf = butter(2, 1.5 / (0.5 * FS), btype='high')
zi_hpf = lfilter_zi(b_hpf, a_hpf) * 512.0

# 3. 35 Hz Butterworth Low-Pass Filter (Removes EMG muscle noise)
b_lpf, a_lpf = butter(4, 35.0 / (0.5 * FS), btype='low')
zi_lpf = lfilter_zi(b_lpf, a_lpf) * 0.0

# 4. QRS Enhancer Bandpass (5 - 18 Hz: Isolates strictly the R-peak energy)
b_qrs, a_qrs = butter(3, [5.0 / (0.5 * FS), 18.0 / (0.5 * FS)], btype='band')
zi_qrs = lfilter_zi(b_qrs, a_qrs) * 0.0

# --- BUFFERS & UI STATE ---
raw_buf = deque([512.0] * BUF_LEN, maxlen=BUF_LEN)
filt_buf = deque([0.0] * BUF_LEN, maxlen=BUF_LEN)

ui_state = {
    '50Hz Notch': True,
    '1.5Hz HPF': True,
    '35Hz LPF': True,
    'QRS Lock': False,     # Check this to isolate heartbeat spikes from coin drift!
    'Smooth/Interp': True,
    'Auto-Scale Y': True,
    'Invert ECG': False
}

# --- SERIAL CONNECTION WITH AUTO-RETRY ---
ser = None
while ser is None:
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=0.01)
        print(f"Connected to {SERIAL_PORT}")
    except serial.serialutil.SerialException:
        print(f"Waiting for {SERIAL_PORT}... Close Arduino IDE if open.")
        time.sleep(1.5)

ser.reset_input_buffer()

# --- PLOT SETUP ---
fig, (ax_raw, ax_filt) = plt.subplots(2, 1, figsize=(11.5, 6.5), sharex=True)
plt.subplots_adjust(left=0.08, right=0.75, hspace=0.3)

t_axis = np.linspace(-WINDOW_SEC, 0, BUF_LEN)
line_raw, = ax_raw.plot(t_axis, raw_buf, color='#ef4444', lw=1)
ax_raw.set_title("Raw Analog ECG (Centered at 2.5V / ADC 512)")
ax_raw.set_ylabel("ADC (0-1023)")
ax_raw.set_ylim(*FIXED_RAW_LIM)
ax_raw.grid(True, alpha=0.3)

line_filt, = ax_filt.plot(t_axis, filt_buf, color='#10b981', lw=1.6)
ax_filt.set_title("Filtered & Interpolated ECG (Notch + Bandpass + SavGol + QRS Lock)")
ax_filt.set_xlabel("Time (s)")
ax_filt.set_ylabel("Amplitude")
ax_filt.set_ylim(*FIXED_FILT_LIM)
ax_filt.grid(True, alpha=0.3)

# --- INTERACTIVE CHECKBOXES ---
rax = plt.axes([0.77, 0.25, 0.21, 0.48])
check = CheckButtons(rax, list(ui_state.keys()), list(ui_state.values()))

def toggle_option(label):
    ui_state[label] = not ui_state[label]

check.on_clicked(toggle_option)

def update(frame):
    global zi_notch, zi_notch2, zi_hpf, zi_lpf, zi_qrs
    lines = []
    while ser.in_waiting:
        try:
            line = ser.readline().decode('utf-8', errors='ignore').strip()
            if line:
                val = float(line)
                if 0.0 <= val <= 1023.0:
                    lines.append(val)
        except ValueError:
            pass

    if lines:
        x = np.array(lines)
        raw_buf.extend(x)

        y = x.copy()
        if ui_state['50Hz Notch']:
            y, zi_notch = lfilter(b_notch, a_notch, y, zi=zi_notch)
            y, zi_notch2 = lfilter(b_notch2, a_notch2, y, zi=zi_notch2)
        if ui_state['1.5Hz HPF']:
            y, zi_hpf = lfilter(b_hpf, a_hpf, y, zi=zi_hpf)
        if ui_state['35Hz LPF']:
            y, zi_lpf = lfilter(b_lpf, a_lpf, y, zi=zi_lpf)
        if ui_state['QRS Lock']:
            y, zi_qrs = lfilter(b_qrs, a_qrs, y, zi=zi_qrs)

        if ui_state['Invert ECG']:
            y = -y

        filt_buf.extend(y)

        # Apply 3-point median glitch filter + 11-point Savitzky-Golay polynomial interpolation
        display_y = np.array(filt_buf)
        if ui_state['Smooth/Interp']:
            display_y = medfilt(display_y, kernel_size=3)
            display_y = savgol_filter(display_y, window_length=11, polyorder=3)

        line_raw.set_ydata(raw_buf)
        line_filt.set_ydata(display_y)

        # Handle Auto-Scale Y Toggle
        if ui_state['Auto-Scale Y']:
            r_min, r_max = min(raw_buf), max(raw_buf)
            f_min, f_max = np.min(display_y), np.max(display_y)
            ax_raw.set_ylim(r_min - 25, r_max + 25)
            ax_filt.set_ylim(f_min - 10, f_max + 10)
        else:
            ax_raw.set_ylim(*FIXED_RAW_LIM)
            ax_filt.set_ylim(*FIXED_FILT_LIM)

    return line_raw, line_filt

ani = FuncAnimation(fig, update, interval=30, blit=False, cache_frame_data=False)
plt.show()