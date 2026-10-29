# 🫀 Low-Cost 3-Op-Amp ECG Monitoring System & Real-Time Python DSP

![ECG Output Waveform](media/output_waveform.png)

## 📌 Overview
This project implements a complete end-to-end **Electrocardiogram (ECG) Data Acquisition and Digital Signal Processing (DSP) System**. Using a single **TL074CN** Quad JFET-Input Operational Amplifier configured as a classic 3-op-amp instrumentation amplifier, the hardware extracts millivolt-level cardiac bio-potentials ($\sim 1\text{ mV}$) in the presence of heavy $50\text{ Hz}$ mains interference and galvanic skin-electrode offsets. 

The amplified analog signal is AC-coupled, level-shifted to $2.5\text{V}$, digitized at $500\text{ Hz}$ via an Arduino ADC, and streamed over UART to a custom real-time **Python DSP Dashboard** featuring toggleable IIR and Butterworth filter stages.

---

## ⚙️ Hardware Architecture & Schematic

![Circuit Schematic](hardware/schematic_ecg.png)

### 1. Input Protection & Bias Return Path
* **Current-Limiting Resistors ($10\text{ k}\Omega$):** Placed in series with both the Left Arm (`LA / Chest+`) and Right Arm (`RA / Chest-`) leads to protect the subject and limit fault currents.
* **JFET Bias Return ($1\text{ M}\Omega$ to VGND):** Provides a DC bias current return path to virtual ground (`VGND`) for the floating non-inverting inputs (`Pin 3` and `Pin 5`) while maintaining high input impedance ($\approx 1\text{ M}\Omega$ effective, with internal JFET impedance $> 10^{12}\text{ }\Omega$).
* **Reference Electrode (`RL / Ref`):** Ties the body directly to `VGND` ($0\text{V}$ split-rail midpoint) to establish a common-mode reference and suppress ambient $50\text{ Hz}$ hum.

### 2. Stage 1: Differential Pre-Amplifier (Op-Amps 1 & 2)
Built using two op-amps of the `TL074CN` (`Pins 1, 2, 3` and `Pins 5, 6, 7`) sharing a central gain resistor $R_{\text{gain}} = 500\text{ }\Omega$ (implemented via two $1\text{ k}\Omega$ resistors in parallel) and feedback resistors $R_{f1} = 10\text{ k}\Omega$:

$$A_{v1} = 1 + \frac{2 R_{f1}}{R_{\text{gain}}} = 1 + \frac{2(10\text{ k}\Omega)}{500\text{ }\Omega} = 1 + 40 = 41\text{ V/V}$$

### 3. Stage 2: Difference Amplifier / Subtractor (Op-Amp 3)
Op-Amp 3 (`Pins 8, 9, 10`) rejects common-mode noise and amplifies the differential signal using input resistors $R_{\text{in}} = 1\text{ k}\Omega$ and feedback/ground resistors $R_{f2} = 10\text{ k}\Omega$:

$$A_{v2} = \frac{R_{f2}}{R_{\text{in}}} = \frac{10\text{ k}\Omega}{1\text{ k}\Omega} = 10\text{ V/V}$$

### 4. Total Hardware Gain
$$A_{v(\text{total})} = A_{v1} \times A_{v2} = 41 \times 10 = 410\text{ V/V} \quad (\approx 52.26\text{ dB})$$

### 5. Output AC-Coupling & $2.5\text{V}$ DC Level Shifter
* **DC Blocking Capacitor ($C = 1\text{ }\mu\text{F}$):** Blocks wandering half-cell DC offsets generated at the skin-electrode interface.
* **Mid-Supply Bias Divider ($100\text{ k}\Omega \parallel 100\text{ k}\Omega$):** Biases the Arduino `A0` input at $+2.5\text{V}$ ($\text{ADC Count } \approx 512$) between $+5\text{V}$ and `GND`.
* **Analog High-Pass Cutoff Frequency ($f_c$):**
  $$R_{\text{eq}} = 100\text{ k}\Omega \parallel 100\text{ k}\Omega = 50\text{ k}\Omega$$
  $$f_c = \frac{1}{2\pi R_{\text{eq}} C} = \frac{1}{2\pi (50\text{ k}\Omega)(1\text{ }\mu\text{F})} \approx 3.18\text{ Hz}$$

---

## 🔌 TL074CN IC Pinout & Wiring Diagram

```text
                             TL074CN (14-Pin DIP)
                                 +----v----+
     Stage 1A Out (to 1k & 10k) -| 1    14 |- NC (Unused Amp 4 Out)
     Stage 1A Inv (10k & Rgain) -| 2    13 |- Pin 12 (Unused Amp 4 Inv - Tied as Follower)
    LA / Chest+ (via 10k & 1M)  -| 3    12 |- VGND (Unused Amp 4 Non-Inv Tied to GND)
            +Vcc (+4.5V Rail)   -| 4    11 |- -Vee (-4.5V Rail)
    RA / Chest- (via 10k & 1M)  -| 5    10 |- Stage 2 Non-Inv (1k from Pin 7 & 10k to VGND)
     Stage 1B Inv (10k & Rgain) -| 6     9 |- Stage 2 Inv (1k from Pin 1 & 10k from Pin 8)
     Stage 1B Out (to 1k & 10k) -| 7     8 |- Stage 2 Out (Final Analog Out -> 1uF Cap)
                                 +---------+
```

### Pin-by-Pin Connection Table
| Pin | Symbol | Function / Circuit Connection |
| :--- | :--- | :--- |
| **Pin 1** | `1OUT` | Stage 1 Upper Pre-Amp Output $\rightarrow$ $10\text{ k}\Omega$ feedback to `Pin 2` & $1\text{ k}\Omega$ to `Pin 9` |
| **Pin 2** | `1IN-` | Stage 1 Upper Inverting Input $\rightarrow$ $10\text{ k}\Omega$ from `Pin 1` & $500\text{ }\Omega$ ($1\text{k} \parallel 1\text{k}$) to `Pin 6` |
| **Pin 3** | `1IN+` | Stage 1 Upper Non-Inverting Input $\rightarrow$ $10\text{ k}\Omega$ to `LA / Chest+` & $1\text{ M}\Omega$ to `VGND` |
| **Pin 4** | `VCC+` | Positive Split-Rail Supply ($+4.5\text{V}$) |
| **Pin 5** | `2IN+` | Stage 1 Lower Non-Inverting Input $\rightarrow$ $10\text{ k}\Omega$ to `RA / Chest-` & $1\text{ M}\Omega$ to `VGND` |
| **Pin 6** | `2IN-` | Stage 1 Lower Inverting Input $\rightarrow$ $10\text{ k}\Omega$ from `Pin 7` & $500\text{ }\Omega$ ($1\text{k} \parallel 1\text{k}$) to `Pin 2` |
| **Pin 7** | `2OUT` | Stage 1 Lower Pre-Amp Output $\rightarrow$ $10\text{ k}\Omega$ feedback to `Pin 6` & $1\text{ k}\Omega$ to `Pin 10` |
| **Pin 8** | `3OUT` | Stage 2 Subtractor Output $\rightarrow$ $10\text{ k}\Omega$ feedback to `Pin 9` & $1\text{ }\mu\text{F}$ cap to `Arduino A0` |
| **Pin 9** | `3IN-` | Stage 2 Subtractor Inverting Input $\rightarrow$ $1\text{ k}\Omega$ from `Pin 1` & $10\text{ k}\Omega$ from `Pin 8` |
| **Pin 10** | `3IN+` | Stage 2 Subtractor Non-Inverting Input $\rightarrow$ $1\text{ k}\Omega$ from `Pin 7` & $10\text{ k}\Omega$ to `VGND` |
| **Pin 11** | `VCC-` | Negative Split-Rail Supply ($-4.5\text{V}$) |
| **Pins 12–14** | `AMP 4` | Unused 4th Op-Amp (Configured as unity buffer tied to `VGND` to prevent oscillation) |

---

## 💻 Real-Time Python DSP Pipeline
The raw $500\text{ Hz}$ ADC stream is processed in real time using `scipy.signal`:
1. **Cascaded IIR Notch Filters ($50\text{ Hz}$ & $100\text{ Hz}$, $Q = 25$):** Eliminates fundamental AC powerline hum and its second harmonic.
2. **2nd-Order Butterworth High-Pass Filter ($f_c = 1.5\text{ Hz}$):** Suppresses respiration-induced baseline wander and electrode motion artifacts.
3. **4th-Order Butterworth Low-Pass Filter ($f_c = 35\text{ Hz}$):** Attenuates high-frequency electromyographic (EMG) muscle tremor and thermal noise.
4. **QRS Bandpass Enhancer ($5\text{ Hz} - 18\text{ Hz}$):** Optional toggle to isolate R-peak energy for heart-rate detection.
5. **Median + Savitzky-Golay Filtering:** 3-point median spike suppressor followed by an 11-point, 3rd-order polynomial smoother to preserve sharp QRS morphology.

---

## 🚀 Getting Started

### 1. Flash the Arduino Firmware
Upload `firmware/ecg_adc_streamer/ecg_adc_streamer.ino` to your Arduino Uno/Nano (samples `A0` at $500\text{ Hz}$ over `115200` baud).

### 2. Run the Python DSP Dashboard
```bash
pip install numpy scipy matplotlib pyserial
python software/ecg_dsp_dashboard.py
```
*Note: Update `SERIAL_PORT = 'COM4'` in `ecg_dsp_dashboard.py` to match your system's serial port.*