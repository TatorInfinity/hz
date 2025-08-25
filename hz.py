import numpy as np
import sounddevice as sd
import tkinter as tk
from tkinter import ttk
import threading
import time
import json

# --- Global variables ---
play_thread = None
playing = False
sample_rate = 44100

# --- Settings ---
frequencies = {"left":210.0, "right":220.0, "top":10.0}
positions = {"left":[0,0,0], "right":[0,0,0], "top":[0,0,0]}
volume = 0.5  # 0 to 1


root = tk.Tk()
root.title("hz")

linked = tk.BooleanVar(value=True)
stereo_mode = tk.BooleanVar(value=True)

# --- Audio generation ---
def generate_buffer(freqs, positions, duration=0.1):
    t = np.linspace(0, duration, int(sample_rate*duration), endpoint=False)
    left_wave = np.sin(2*np.pi*freqs["left"]*t)
    right_wave = np.sin(2*np.pi*freqs["right"]*t)
    top_wave = np.sin(2*np.pi*freqs["top"]*t)

    def pan_and_attenuate(wave, pos):
        x, y, z = pos
        left_gain = np.clip(1 - (x+1)/2, 0, 1)
        right_gain = np.clip((x+1)/2, 0, 1)
        distance = np.clip(1 - z/10.0, 0, 1)
        return wave*distance*left_gain, wave*distance*right_gain

    l1,r1 = pan_and_attenuate(left_wave, positions["left"])
    l2,r2 = pan_and_attenuate(right_wave, positions["right"])
    l3,r3 = pan_and_attenuate(top_wave, positions["top"])

    left_channel = (l1+l2+l3)*volume
    right_channel = (r1+r2+r3)*volume

    # Normalize
    max_val = max(np.max(np.abs(left_channel)), np.max(np.abs(right_channel)), 1e-6)
    left_channel /= max_val
    right_channel /= max_val

    if stereo_mode.get():
        return np.column_stack((left_channel,right_channel)).astype(np.float32)
    else:
        mono = (left_channel+right_channel)/2
        return np.column_stack((mono,mono)).astype(np.float32)

# --- Playback loop ---
def playback_loop():
    global playing
    while playing:
        try:
            buffer = generate_buffer(frequencies, positions)
            sd.play(buffer, samplerate=sample_rate, blocking=True)
        except Exception as e:
            print("Playback error:", e)
            time.sleep(0.1)

# --- Start/stop ---
def start_play():
    global play_thread, playing
    if playing: return
    playing = True
    play_thread = threading.Thread(target=playback_loop)
    play_thread.daemon = True
    play_thread.start()

def stop_play():
    global playing
    playing = False
    sd.stop()

# --- Update beat if linked ---
def update_beat(*args):
    if linked.get():
        try:
            beat_freq.set(str(round(abs(frequencies["right"]-frequencies["left"]),2)))
        except: pass

# --- Auto-set tones ---
def auto_set_tones():
    try:
        target = float(target_freq.get())
        beat = float(beat_freq.get())
    except: return
    frequencies["left"] = target - beat/2
    frequencies["right"] = target + beat/2
    left_entry_var.set(str(round(frequencies["left"],2)))
    right_entry_var.set(str(round(frequencies["right"],2)))
    update_beat()

# --- Apply pasted JSON/CSV ---
def apply_settings():
    text = paste_text.get("1.0", tk.END)
    try:
        data = json.loads(text)
        if "frequencies" in data:
            for k in data["frequencies"]: frequencies[k]=data["frequencies"][k]
        if "positions" in data:
            for k in data["positions"]: positions[k]=data["positions"][k]
        if "volume" in data:
            global volume
            volume = float(data["volume"])
        # Update UI fields
        left_entry_var.set(str(frequencies["left"]))
        right_entry_var.set(str(frequencies["right"]))
        top_entry_var.set(str(frequencies["top"]))
        left_x.set(positions["left"][0])
        right_x.set(positions["right"][0])
        top_x.set(positions["top"][0])
    except Exception as e:
        print("Error applying settings:", e)

# --- GUI ---
frame = ttk.Frame(root, padding=10)
frame.pack()

# Frequencies
ttk.Label(frame,text="Left Frequency (Hz)").grid(row=0,column=0)
left_entry_var = tk.StringVar(value=str(frequencies["left"]))
ttk.Entry(frame,textvariable=left_entry_var).grid(row=0,column=1)

ttk.Label(frame,text="Right Frequency (Hz)").grid(row=1,column=0)
right_entry_var = tk.StringVar(value=str(frequencies["right"]))
ttk.Entry(frame,textvariable=right_entry_var).grid(row=1,column=1)

ttk.Label(frame,text="Top/Sub Frequency (Hz)").grid(row=2,column=0)
top_entry_var = tk.StringVar(value=str(frequencies["top"]))
ttk.Entry(frame,textvariable=top_entry_var).grid(row=2,column=1)

# Beat
ttk.Label(frame,text="Target Beat (Hz)").grid(row=3,column=0)
beat_freq = tk.StringVar(value=str(abs(frequencies["right"]-frequencies["left"])))
ttk.Entry(frame,textvariable=beat_freq,state="readonly").grid(row=3,column=1)

# Link/auto
ttk.Checkbutton(frame,text="Link Left/Right to Beat",variable=linked).grid(row=4,column=0,columnspan=2)
ttk.Label(frame,text="Target High Frequency").grid(row=5,column=0)
target_freq = tk.StringVar(value="20000")
ttk.Entry(frame,textvariable=target_freq).grid(row=5,column=1)
ttk.Button(frame,text="Auto Set Tones",command=auto_set_tones).grid(row=6,column=0,columnspan=2,pady=5)

# Volume
ttk.Label(frame,text="Volume").grid(row=7,column=0)
volume_slider = tk.DoubleVar(value=volume)
ttk.Scale(frame,from_=0,to=1,variable=volume_slider,orient="horizontal").grid(row=7,column=1)

# Playback
ttk.Button(frame,text="Start Loop",command=start_play).grid(row=8,column=0)
ttk.Button(frame,text="Stop",command=stop_play).grid(row=8,column=1)
ttk.Checkbutton(frame,text="Stereo Mode",variable=stereo_mode).grid(row=9,column=0,columnspan=2)

# Panning
ttk.Label(frame,text="Left X").grid(row=10,column=0)
left_x = tk.DoubleVar(value=positions["left"][0])
ttk.Scale(frame,from_=-1,to=1,variable=left_x,orient="horizontal").grid(row=10,column=1)
ttk.Label(frame,text="Right X").grid(row=11,column=0)
right_x = tk.DoubleVar(value=positions["right"][0])
ttk.Scale(frame,from_=-1,to=1,variable=right_x,orient="horizontal").grid(row=11,column=1)
ttk.Label(frame,text="Top X").grid(row=12,column=0)
top_x = tk.DoubleVar(value=positions["top"][0])
ttk.Scale(frame,from_=-1,to=1,variable=top_x,orient="horizontal").grid(row=12,column=1)

# Paste box
ttk.Label(frame,text="Paste JSON Settings Here").grid(row=13,column=0,columnspan=2)
paste_text = tk.Text(frame,height=6,width=40)
paste_text.grid(row=14,column=0,columnspan=2)
ttk.Button(frame,text="Apply Pasted Settings",command=apply_settings).grid(row=15,column=0,columnspan=2,pady=5)

# --- Update values in real-time ---
def update_values(*args):
    global volume
    try: frequencies["left"]=float(left_entry_var.get())
    except: pass
    try: frequencies["right"]=float(right_entry_var.get())
    except: pass
    try: frequencies["top"]=float(top_entry_var.get())
    except: pass
    positions["left"][0]=left_x.get()
    positions["right"][0]=right_x.get()
    positions["top"][0]=top_x.get()
    volume = volume_slider.get()
    update_beat()

for var in [left_entry_var,right_entry_var,top_entry_var,left_x,right_x,top_x,volume_slider]:
    var.trace_add("write",update_values)

root.mainloop()

