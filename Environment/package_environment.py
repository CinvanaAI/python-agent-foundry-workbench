from pathlib import Path

import tkinter as tk
from tkinter import messagebox

try:
    from PIL import Image, ImageTk
except ImportError as exc:
    raise ImportError(
        "PackageEnvironmentView requires Pillow. Install it with: pip install pillow"
    ) from exc


class PackageEnvironmentView:
    def __init__(self, parent: tk.Widget) -> None:
        self.parent = parent
        self.base_dir = Path(__file__).resolve().parent
        self.skins_dir = self.base_dir / "Skins"
        self.default_skin_path = self.skins_dir / "arcane_archives.png"

        self.container = tk.Frame(parent, bg="black")
        self.container.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(
            self.container,
            highlightthickness=0,
            bd=0,
            bg="black",
        )
        self.canvas.pack(fill="both", expand=True)

        self._original_image: Image.Image | None = None
        self._rendered_image: ImageTk.PhotoImage | None = None
        self._image_item: int | None = None
        self._message_item: int | None = None

        self._display_left = 0
        self._display_top = 0
        self._display_scale = 1.0

        self._load_default_skin()

        self.canvas.bind("<Configure>", self._handle_canvas_resize)

    def _load_default_skin(self) -> None:
        if not self.default_skin_path.exists():
            self._draw_missing_skin_message(
                f"Missing skin:\n{self.default_skin_path.name}"
            )
            return

        self._original_image = Image.open(self.default_skin_path)
        self._redraw_background()

    def _handle_canvas_resize(self, event=None) -> None:
        if self._original_image is None:
            return
        self._redraw_background()

    def _redraw_background(self) -> None:
        if self._original_image is None:
            return

        self.canvas.delete("hotspot")

        canvas_width = max(self.canvas.winfo_width(), 1)
        canvas_height = max(self.canvas.winfo_height(), 1)

        image_width, image_height = self._original_image.size
        scale = min(canvas_width / image_width, canvas_height / image_height)

        resized_width = max(1, int(image_width * scale))
        resized_height = max(1, int(image_height * scale))

        resized_image = self._original_image.resize(
            (resized_width, resized_height),
            Image.LANCZOS,
        )

        left = max((resized_width - canvas_width) // 2, 0)
        top = max((resized_height - canvas_height) // 2, 0)
        right = left + canvas_width
        bottom = top + canvas_height

        cropped_image = resized_image.crop((left, top, right, bottom))
        self._rendered_image = ImageTk.PhotoImage(cropped_image)

        self._display_left = left
        self._display_top = top
        self._display_scale = scale

        if self._image_item is None:
            self._image_item = self.canvas.create_image(
                0,
                0,
                anchor="nw",
                image=self._rendered_image,
            )
        else:
            self.canvas.itemconfigure(self._image_item, image=self._rendered_image)

        self.canvas.coords(self._image_item, 0, 0)

        if self._message_item is not None:
            self.canvas.delete(self._message_item)
            self._message_item = None

        self._build_hotspots()

    def _draw_missing_skin_message(self, message: str) -> None:
        self.canvas.delete("all")
        self._image_item = None
        self._rendered_image = None
        self._message_item = self.canvas.create_text(
            24,
            24,
            anchor="nw",
            text=message,
            fill="white",
            font=("Segoe UI", 16, "bold"),
        )

    def _image_to_canvas_coords(self, x: float, y: float) -> tuple[float, float]:
        canvas_x = (x * self._display_scale) - self._display_left
        canvas_y = (y * self._display_scale) - self._display_top
        return canvas_x, canvas_y

    def _build_hotspots(self) -> None:
        self._build_scribe_hotspot()
        self._build_settings_hotspot()
        self._build_reliquary_hotspot()
        self._build_scriptorium_hotspot()
        self._build_codex_hotspot()
        self._build_dispatch_hotspot()
        self._build_return_hotspot()

    def _create_debug_hotspot(
        self,
        tag_name: str,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        outline_color: str,
        click_handler,
    ) -> None:
        cx1, cy1 = self._image_to_canvas_coords(x1, y1)
        cx2, cy2 = self._image_to_canvas_coords(x2, y2)

        self.canvas.create_rectangle(
            cx1,
            cy1,
            cx2,
            cy2,
            outline=outline_color,
            width=2,
            fill="",
            tags=("hotspot", tag_name),
        )

        self.canvas.tag_bind(tag_name, "<Enter>", self._on_hotspot_enter)
        self.canvas.tag_bind(tag_name, "<Leave>", self._on_hotspot_leave)
        self.canvas.tag_bind(tag_name, "<Button-1>", click_handler)

    def _build_scribe_hotspot(self) -> None:
        if self._original_image is None:
            return

        self._create_debug_hotspot(
            tag_name="scribe_new_manuscript",
            x1=52,
            y1=295,
            x2=415,
            y2=372,
            outline_color="red",
            click_handler=self._on_scribe_click,
        )

    def _build_settings_hotspot(self) -> None:
        if self._original_image is None:
            return

        self._create_debug_hotspot(
            tag_name="settings",
            x1=18,
            y1=58,
            x2=76,
            y2=116,
            outline_color="deepskyblue",
            click_handler=self._on_settings_click,
        )

    def _build_reliquary_hotspot(self) -> None:
        if self._original_image is None:
            return

        self._create_debug_hotspot(
            tag_name="reliquary_vault",
            x1=995,
            y1=270,
            x2=1252,
            y2=355,
            outline_color="deepskyblue",
            click_handler=self._on_reliquary_click,
        )

    def _build_scriptorium_hotspot(self) -> None:
        if self._original_image is None:
            return

        self._create_debug_hotspot(
            tag_name="scriptorium",
            x1=760,
            y1=560,
            x2=1045,
            y2=662,
            outline_color="deepskyblue",
            click_handler=self._on_scriptorium_click,
        )

    def _build_codex_hotspot(self) -> None:
        if self._original_image is None:
            return

        self._create_debug_hotspot(
            tag_name="codex_of_records",
            x1=225,
            y1=742,
            x2=840,
            y2=954,
            outline_color="deepskyblue",
            click_handler=self._on_codex_click,
        )

    def _build_dispatch_hotspot(self) -> None:
        if self._original_image is None:
            return

        self._create_debug_hotspot(
            tag_name="dispatch_desk",
            x1=1245,
            y1=1004,
            x2=1572,
            y2=1103,
            outline_color="deepskyblue",
            click_handler=self._on_dispatch_click,
        )

    def _build_return_hotspot(self) -> None:
        if self._original_image is None:
            return

        self._create_debug_hotspot(
            tag_name="return_to_archivist",
            x1=20,
            y1=1006,
            x2=360,
            y2=1165,
            outline_color="deepskyblue",
            click_handler=self._on_return_click,
        )

    def _on_hotspot_enter(self, event=None) -> None:
        self.canvas.config(cursor="hand2")

    def _on_hotspot_leave(self, event=None) -> None:
        self.canvas.config(cursor="")

    def _on_scribe_click(self, event=None) -> None:
        messagebox.showinfo("Packages Environment", "Scribe New Manuscript clicked")

    def _on_settings_click(self, event=None) -> None:
        messagebox.showinfo("Packages Environment", "Settings clicked")

    def _on_reliquary_click(self, event=None) -> None:
        messagebox.showinfo("Packages Environment", "Reliquary Vault clicked")

    def _on_scriptorium_click(self, event=None) -> None:
        messagebox.showinfo("Packages Environment", "Scriptorium clicked")

    def _on_codex_click(self, event=None) -> None:
        messagebox.showinfo("Packages Environment", "Codex of Records clicked")

    def _on_dispatch_click(self, event=None) -> None:
        messagebox.showinfo("Packages Environment", "Dispatch Desk clicked")

    def _on_return_click(self, event=None) -> None:
        messagebox.showinfo("Packages Environment", "Return to Archivist clicked")