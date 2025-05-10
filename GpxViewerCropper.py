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
        self.hover_line_route = None
        self.hover_line_elev = None
        self.route_marker = None
        self.elev_marker = None

        # Main layout
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.left_frame = tk.Frame(self.main_frame)
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.right_frame = tk.Frame(self.main_frame)
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Controls and metadata on the left
        self.load_btn = tk.Button(self.left_frame, text="Load GPX", command=self.load_gpx)
        self.load_btn.pack()

        self.meta_label = tk.Label(self.left_frame, text="No GPX loaded")
        self.meta_label.pack()

        # Elevation plot (top of left side)
        self.fig_elev, self.ax_elev = plt.subplots(figsize=(5, 2))
        self.canvas_elev = FigureCanvasTkAgg(self.fig_elev, master=self.left_frame)
        self.canvas_elev.get_tk_widget().pack()
        self.canvas_elev.mpl_connect("motion_notify_event", self.on_hover)

        # Route plot (right side)
        self.fig_route, self.ax_route = plt.subplots(figsize=(5, 4))
        self.canvas_route = FigureCanvasTkAgg(self.fig_route, master=self.right_frame)
        self.canvas_route.get_tk_widget().pack()
        self.canvas_route.mpl_connect("motion_notify_event", self.on_hover)

        # Crop inputs
        self.crop_frame = tk.Frame(self.left_frame)
        self.crop_frame.pack()

        tk.Label(self.crop_frame, text="Start Index:").pack(side=tk.LEFT)
        self.start_entry = tk.Entry(self.crop_frame, width=5)
        self.start_entry.pack(side=tk.LEFT)

        tk.Label(self.crop_frame, text="End Index:").pack(side=tk.LEFT)
        self.end_entry = tk.Entry(self.crop_frame, width=5)
        self.end_entry.pack(side=tk.LEFT)

        self.crop_btn = tk.Button(self.left_frame, text="Crop & Save", command=self.crop_and_save)
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

        self.lats = [p.latitude for p in self.points]
        self.lons = [p.longitude for p in self.points]
        self.elevs = [p.elevation for p in self.points]

        self.ax_route.plot(self.lons, self.lats, color='blue')
        self.ax_route.set_title("Route")
        self.ax_route.set_facecolor('white')

        self.ax_elev.plot(self.elevs, color='green')
        self.ax_elev.set_title("Elevation Profile")
        self.ax_elev.set_facecolor('white')

        self.fig_route.tight_layout()
        self.fig_elev.tight_layout()
        self.canvas_route.draw()
        self.canvas_elev.draw()

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

    def on_hover(self, event):
        if not self.points or event.inaxes not in [self.ax_route, self.ax_elev]:
            return

        if event.inaxes == self.ax_elev:
            index = int(event.xdata) if event.xdata and 0 <= int(event.xdata) < len(self.points) else None
        else:
            index = self.find_closest_index_by_lon(event.xdata) if event.xdata else None

        if index is None or not (0 <= index < len(self.points)):
            return

        # Clear previous markers
        if self.route_marker:
            self.route_marker.remove()
        if self.elev_marker:
            self.elev_marker.remove()

        self.route_marker = self.ax_route.plot(self.lons[index], self.lats[index], 'ro')[0]
        self.elev_marker = self.ax_elev.plot(index, self.elevs[index], 'ro')[0]

        self.canvas_route.draw()
        self.canvas_elev.draw()

    def find_closest_index_by_lon(self, lon):
        if not self.lons:
            return None
        return min(range(len(self.lons)), key=lambda i: abs(self.lons[i] - lon))

if __name__ == '__main__':
    root = tk.Tk()
    app = GPXViewer(root)
    root.mainloop()