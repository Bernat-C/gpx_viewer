import tkinter as tk
from tkinter import filedialog, messagebox
import gpxpy
import gpxpy.gpx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

class GPXViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("GPX Viewer and Cropper")

        self.gpx = None
        self.points = []

        # UI setup
        self.load_btn = tk.Button(root, text="Load GPX", command=self.load_gpx)
        self.load_btn.pack()

        self.meta_label = tk.Label(root, text="No GPX loaded")
        self.meta_label.pack()

        self.fig, (self.ax_route, self.ax_elev) = plt.subplots(2, 1, figsize=(5, 5))
        self.canvas = FigureCanvasTkAgg(self.fig, master=root)
        self.canvas.get_tk_widget().pack()

        self.crop_frame = tk.Frame(root)
        self.crop_frame.pack()

        tk.Label(self.crop_frame, text="Start Index:").pack(side=tk.LEFT)
        self.start_entry = tk.Entry(self.crop_frame, width=5)
        self.start_entry.pack(side=tk.LEFT)

        tk.Label(self.crop_frame, text="End Index:").pack(side=tk.LEFT)
        self.end_entry = tk.Entry(self.crop_frame, width=5)
        self.end_entry.pack(side=tk.LEFT)

        self.crop_btn = tk.Button(root, text="Crop & Save", command=self.crop_and_save)
        self.crop_btn.pack()

    def load_gpx(self):
        file_path = filedialog.askopenfilename(filetypes=[("GPX files", "*.gpx")])
        if not file_path:
            return

        with open(file_path, 'r') as gpx_file:
            self.gpx = gpxpy.parse(gpx_file)
            self.extract_points()
            self.display_route_and_elevation()
            self.display_metadata()

    def extract_points(self):
        self.points = []
        for track in self.gpx.tracks:
            for segment in track.segments:
                for point in segment.points:
                    self.points.append(point)

    def display_route_and_elevation(self):
        self.ax_route.clear()
        self.ax_elev.clear()

        if not self.points:
            return

        lats = [p.latitude for p in self.points]
        lons = [p.longitude for p in self.points]
        elevs = [p.elevation for p in self.points]

        self.ax_route.plot(lons, lats, color='blue')
        self.ax_route.set_title("Route")
        self.ax_route.set_facecolor('white')

        self.ax_elev.plot(elevs, color='green')
        self.ax_elev.set_title("Elevation Profile")
        self.ax_elev.set_facecolor('white')

        self.fig.tight_layout()
        self.canvas.draw()

    def display_metadata(self):
        total_distance = self.gpx.length_2d() / 1000  # in km
        duration = self.gpx.get_duration() / 3600 if self.gpx.get_duration() else 0  # in hours
        self.meta_label.config(text=f"Points: {len(self.points)} | Distance: {total_distance:.2f} km | Duration: {duration:.2f} hrs")

    def crop_and_save(self):
        try:
            start = int(self.start_entry.get())
            end = int(self.end_entry.get())
            if start < 0 or end > len(self.points) or start >= end:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid start and end indices.")
            return

        cropped_gpx = gpxpy.gpx.GPX()
        track = gpxpy.gpx.GPXTrack()
        cropped_gpx.tracks.append(track)
        segment = gpxpy.gpx.GPXTrackSegment()
        track.segments.append(segment)

        for p in self.points[start:end]:
            segment.points.append(gpxpy.gpx.GPXTrackPoint(p.latitude, p.longitude, elevation=p.elevation, time=p.time))

        save_path = filedialog.asksaveasfilename(defaultextension=".gpx", filetypes=[("GPX files", "*.gpx")])
        if not save_path:
            return

        with open(save_path, 'w') as f:
            f.write(cropped_gpx.to_xml())

        messagebox.showinfo("Saved", f"Cropped GPX saved to {os.path.basename(save_path)}")

if __name__ == '__main__':
    root = tk.Tk()
    app = GPXViewer(root)
    root.mainloop()
