import os
import subprocess
import re
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from scenedetect import VideoManager, SceneManager
from scenedetect.detectors import ContentDetector

# Use bundled FFmpeg
FFMPEG_PATH = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")

def detect_scene_split(file_path):
    video_manager = VideoManager([file_path])
    scene_manager = SceneManager()
    scene_manager.add_detector(ContentDetector(threshold=30.0))
    video_manager.start()
    scene_manager.detect_scenes(frame_source=video_manager)
    scene_list = scene_manager.get_scene_list()
    duration = video_manager.get_base_timecode().get_frames() / video_manager.get_framerate()
    midpoint = duration / 2
    split_time = min(scene_list, key=lambda x: abs(x[0].get_seconds() - midpoint))[0].get_seconds()
    video_manager.release()
    return int(split_time)

def split_video(input_file, split_seconds, output_file1, output_file2):
    subprocess.run([FFMPEG_PATH, "-y", "-i", input_file, "-t", str(split_seconds), "-c", "copy", output_file1], check=True)
    subprocess.run([FFMPEG_PATH, "-y", "-ss", str(split_seconds), "-i", input_file, "-c", "copy", output_file2], check=True)

def get_titles(ep_code, title_mapping):
    return title_mapping.get(ep_code, ["Part 1", "Part 2"])

def process_folder(source_folder, output_folder, show_name, json_path, progress_var):
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            title_mapping = json.load(f)
    else:
        title_mapping = {}

    mkv_files = [f for root, dirs, files in os.walk(source_folder) for f in files if f.lower().endswith(".mkv")]
    total = len(mkv_files)
    if total == 0:
        messagebox.showerror("Error", "No MKV files found.")
        return

    for idx, filename in enumerate(mkv_files, 1):
        full_path = os.path.join(source_folder, filename)
        try:
            split_sec = detect_scene_split(full_path)
        except:
            continue

        match = re.search(r"S\d+E\d+", filename, re.IGNORECASE)
        ep_code = match.group(0) if match else f"S01E{idx:02d}"

        titles = get_titles(ep_code, title_mapping)

        season_match = re.search(r"S(\d+)", ep_code, re.IGNORECASE)
        season = int(season_match.group(1)) if season_match else 1
        season_folder = os.path.join(output_folder, f"Season {season:02d}")
        os.makedirs(season_folder, exist_ok=True)

        out1 = os.path.join(season_folder, f"{show_name} - {ep_code} - {titles[0]}.mkv")
        out2 = os.path.join(season_folder, f"{show_name} - {ep_code} - {titles[1]}.mkv")

        split_video(full_path, split_sec, out1, out2)

        progress_var.set(int(idx / total * 100))
        root.update_idletasks()

        if ep_code not in title_mapping:
            title_mapping[ep_code] = titles

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(title_mapping, f, indent=2)

    messagebox.showinfo("Done", "Finished splitting!")

def run_gui():
    global root
    root = tk.Tk()
    root.title("Cartoon Episode Splitter")
    root.geometry("550x400")

    tk.Label(root, text="Select Source Folder (raw MKVs)").pack(pady=5)
    src_var = tk.StringVar()
    tk.Entry(root, textvariable=src_var, width=60).pack()
    tk.Button(root, text="Browse", command=lambda: src_var.set(filedialog.askdirectory())).pack()

    tk.Label(root, text="Select Output Folder").pack(pady=5)
    out_var = tk.StringVar()
    tk.Entry(root, textvariable=out_var, width=60).pack()
    tk.Button(root, text="Browse", command=lambda: out_var.set(filedialog.askdirectory())).pack()

    tk.Label(root, text="Show Name").pack(pady=5)
    show_var = tk.StringVar(value="The Loud House")
    tk.Entry(root, textvariable=show_var, width=60).pack()

    tk.Label(root, text="Progress").pack(pady=10)
    progress_var = tk.IntVar()
    progress_bar = ttk.Progressbar(root, variable=progress_var, maximum=100, length=500)
    progress_bar.pack(pady=5)

    tk.Button(root, text="Run Splitter", command=lambda: process_folder(
        src_var.get(), out_var.get(), show_var.get(), "titles_loudhouse.json", progress_var
    )).pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    run_gui()
