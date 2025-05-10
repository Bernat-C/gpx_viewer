import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import gpxpy
import gpxpy.gpx
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import os

class GPXViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("GPX Viewer and Cropper")
        self.root.configure(bg="#ffffff")  # Creamy yellow background

        self.gpx = None
        self.points = []
        self.hover_line_route = None
        self.hover_line_elev = None
        self.route_marker = None
        self.elev_marker = None
        self.select_start = None
        self.select_end = None
        self.start_entry = None
        self.end_entry = None
        self.selecting_crop = False

        # Toolbar
        self.toolbar = tk.Frame(root, bg="#f5deb3", bd=2, relief=tk.RIDGE)
        self.toolbar.pack(side=tk.TOP, fill=tk.X)

        for btn_text, cmd in [
            ("Load GPX", self.load_gpx),
            ("Crop & Save", self.crop_and_save),
            ("Reset Selection", self.reset_selection),
            ("Invert Trail", self.invert_trail)
        ]:
            b = tk.Button(self.toolbar, text=btn_text, command=cmd, bg="#ffe4b5", relief=tk.FLAT, padx=10)
            b.pack(side=tk.LEFT, padx=5, pady=5)

        # Main layout
        self.main_frame = tk.Frame(root, bg="#ffffff")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        self.left_frame = tk.Frame(self.main_frame, bg="#ffffff")
        self.left_frame.pack(side=tk.LEFT, fill=tk.BOTH)

        self.right_frame = tk.Frame(self.main_frame, bg="#ffffff")
        self.right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Metadata (editable)
        self.meta_frame = tk.Frame(self.left_frame, bg="#ffffff")
        self.meta_frame.pack(padx=5, pady=5, anchor="nw")
        self.meta_entries = {}

        # Elevation plot at bottom of left side
        self.fig_elev, self.ax_elev = plt.subplots(figsize=(10, 2))
        self.canvas_elev = FigureCanvasTkAgg(self.fig_elev, master=self.left_frame)
        self.canvas_elev.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.X)
        self.canvas_elev.mpl_connect("motion_notify_event", self.on_hover)
        self.canvas_elev.mpl_connect("button_press_event", self.on_mouse_press)
        self.canvas_elev.mpl_connect("button_release_event", self.on_mouse_release)
        self.canvas_elev.mpl_connect("motion_notify_event", self.on_mouse_drag)

        # Route plot on right side
        self.fig_route, self.ax_route = plt.subplots(figsize=(10, 6))
        self.canvas_route = FigureCanvasTkAgg(self.fig_route, master=self.right_frame)
        self.canvas_route.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        #self.canvas_route.mpl_connect("motion_notify_event", self.on_hover)

    def load_gpx(self):
        filesdir = Path(__file__).parent / r"data"
        file_path = filedialog.askopenfilename(initialdir=filesdir, filetypes=[("GPX files", "*.gpx")])
        if not file_path:
            return

        with open(file_path, 'r') as gpx_file:
            self.gpx = gpxpy.parse(gpx_file)
            self.extract_points()
            
            if self.start_entry:
                self.start_entry.delete(0, tk.END)
                self.start_entry.insert(0, "0")

            if self.end_entry:
                self.end_entry.delete(0, tk.END)
                self.end_entry.insert(0, str(len(self.points)))
        
            self.display_metadata()
            self.display_route_and_elevation()

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

        start = self.get_valid_index(self.start_entry.get(), default=0)
        end = self.get_valid_index(self.end_entry.get(), default=len(self.points))
        end = min(end, len(self.points))
        start = max(start, 0)

        self.ax_route.plot(self.lons[:start], self.lats[:start], color='gray')
        self.ax_route.plot(self.lons[start:end], self.lats[start:end], color='blue')
        self.ax_route.plot(self.lons[end:], self.lats[end:], color='gray')
        self.ax_route.set_title("Route")
        self.ax_route.set_facecolor('#fefcea')

        self.ax_elev.plot(self.elevs, color='green')
        self.ax_elev.axvspan(0, start, color='lightgray', alpha=0.3)
        self.ax_elev.axvspan(start, end, color='gray', alpha=0.5)
        self.ax_elev.axvspan(end, len(self.points), color='lightgray', alpha=0.3)
        self.ax_elev.set_title("Elevation Profile")
        self.ax_elev.set_facecolor('#fefcea')

        self.fig_route.tight_layout()
        self.fig_elev.tight_layout()
        self.canvas_route.draw()
        self.canvas_elev.draw()
        
        self.update_crop_metadata(start, end)

    def display_metadata(self):
        for widget in self.meta_frame.winfo_children():
            widget.destroy()

        total_distance = self.gpx.length_2d() / 1000  # km
        duration = self.gpx.get_duration() / 3600 if self.gpx.get_duration() else 0

        elevation_gain = 0
        elevation_loss = 0
        for i in range(1, len(self.points)):
            delta = self.points[i].elevation - self.points[i - 1].elevation
            if delta > 0:
                elevation_gain += delta
            elif delta < 0:
                elevation_loss += abs(delta)
        
        metadata = {
            "Name": self.gpx.name,
            "Description": self.gpx.description,
            "Author Name": self.gpx.author_name,
            "Author Email": self.gpx.author_email,
            "Time": str(self.gpx.time),
            "Points": str(len(self.points)),
            "Distance (km)": f"{total_distance:.2f}",
            "Duration (hrs)": f"{duration:.2f}",
            "Elevation Gain (m)": f"{elevation_gain:.0f}",
            "Elevation Loss (m)": f"{elevation_loss:.0f}",
            "Start Index": f"{0}",
            "End Index": f"{len(self.points)-1}"
        }

        for i, (key, value) in enumerate(metadata.items()):
            tk.Label(self.meta_frame, text=key+":", anchor="w", bg="#ffffff").grid(row=i, column=0, sticky="w")
            entry = tk.Entry(self.meta_frame, width=60)
            entry.insert(0, str(value) if value is not None else "")
            if key == "Duration (hrs)":
                entry.config(state="normal")
            elif key in ["Name", "Description", "Author Name", "Author Email", "Time", "Duration (hrs)"]:
                entry.config(state="normal")
            elif key in ["Start Index"]:
                entry.config(state="normal")
                self.start_entry = entry
            elif key in ["End Index"]:
                entry.config(state="normal")
                self.end_entry = entry
            else:
                entry.config(state="readonly")
            entry.grid(row=i, column=1, sticky="w")
            self.meta_entries[key] = entry

    def update_crop_metadata(self, start, end):
        if not self.points or start >= end:
            return

        cropped_points = self.points[start:end]
        distance = 0
        gain = 0
        loss = 0

        for i in range(1, len(cropped_points)):
            prev = cropped_points[i - 1]
            curr = cropped_points[i]
            if prev and curr:
                distance += curr.distance_2d(prev)
                if curr.elevation is not None and prev.elevation is not None:
                    delta = curr.elevation - prev.elevation
                    if delta > 0:
                        gain += delta
                    elif delta < 0:
                        loss += abs(delta)

        updates = {
            "Points": str(len(cropped_points)),
            "Distance (km)": f"{distance / 1000:.2f}",
            "Elevation Gain (m)": f"{gain:.0f}",
            "Elevation Loss (m)": f"{loss:.0f}"
        }

        for key, value in updates.items():
            entry = self.meta_entries.get(key)
            if entry:
                entry.config(state="normal")
                entry.delete(0, tk.END)
                entry.insert(0, value)
                entry.config(state="readonly")

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

    def reset_selection(self):
        self.start_entry.delete(0, tk.END)
        self.end_entry.delete(0, tk.END)
        self.display_route_and_elevation()
        
        self.route_marker = None
        self.elev_marker = None

    def invert_trail(self):
        self.points.reverse()
        self.display_route_and_elevation()
        self.display_metadata()

    def on_hover(self, event):
        if not self.points or event.inaxes not in [self.ax_route, self.ax_elev]:
            return

        if event.inaxes == self.ax_elev:
            index = int(event.xdata) if event.xdata and 0 <= int(event.xdata) < len(self.points) else None
        else:
            index = self.find_closest_index_by_lon(event.xdata) if event.xdata else None

        if index is None or not (0 <= index < len(self.points)):
            return

        if self.route_marker is None:
            self.route_marker, = self.ax_route.plot([], [], 'ro')
        if self.elev_marker is None:
            self.elev_marker, = self.ax_elev.plot([], [], 'ro')

        self.route_marker.set_data([self.lons[index]], [self.lats[index]])
        self.elev_marker.set_data([index], [self.elevs[index]])

        self.canvas_route.draw()
        self.canvas_elev.draw()

    def on_mouse_press(self, event):
        if event.inaxes == self.ax_elev and event.xdata is not None:
            x = int(event.xdata)
            self.select_start = max(0, min(x, len(self.points) - 1))
            self.selecting_crop = True

    def on_mouse_release(self, event):
        self.route_marker = None
        self.elev_marker = None
        if event.inaxes == self.ax_elev and event.xdata is not None:
            x = int(event.xdata)
            self.select_end = max(0, min(x, len(self.points) - 1))
            self.selecting_crop = False
            start = min(self.select_start, self.select_end)
            end = max(self.select_start, self.select_end)
            self.start_entry.delete(0, tk.END)
            self.start_entry.insert(0, str(start))
            self.end_entry.delete(0, tk.END)
            self.end_entry.insert(0, str(end))
            self.display_route_and_elevation()

    def on_mouse_drag(self, event):
        if self.selecting_crop and event.inaxes == self.ax_elev and event.xdata is not None:
            x = int(event.xdata)
            self.select_end = max(0, min(x, len(self.points) - 1))
            start = min(self.select_start, self.select_end)
            end = max(self.select_start, self.select_end)
            self.start_entry.delete(0, tk.END)
            self.start_entry.insert(0, str(start))
            self.end_entry.delete(0, tk.END)
            self.end_entry.insert(0, str(end))
            self.display_route_and_elevation()

    def find_closest_index_by_lon(self, lon):
        if not self.lons:
            return None
        return min(range(len(self.lons)), key=lambda i: abs(self.lons[i] - lon))

    def get_valid_index(self, value, default):
        try:
            idx = int(value)
            if 0 <= idx < len(self.points):
                return idx
            return default
        except:
            return default

if __name__ == '__main__':
    root = tk.Tk()
    app = GPXViewer(root)
    root.mainloop()
