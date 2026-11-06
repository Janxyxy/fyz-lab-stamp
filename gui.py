#!/usr/bin/env python3
"""Graphical editor for the lab stamp: fill in the form, see a live preview, save PNG.

Usage:
    python gui.py            # loads data.json if it exists (else data.example.json)
"""
import json
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import ImageTk

from fill_stamp import DATE_FMT, fill_defaults, load_tasks, render_stamp

HERE = Path(__file__).parent
IMAGE = HERE / "razitko.jpg"
DATA = HERE / "data.json"
EXAMPLE = HERE / "data.example.json"

# (key, label) in the order shown in the form; semester/task are handled separately.
TEXT_FIELDS = [
    ("name", "Jméno"),
    ("measurement_date", "Datum měření"),
    ("submission_date", "Datum odevzdání"),
    ("study_year", "Stud. rok"),
    ("year", "Ročník"),
    ("study_group", "Stud. skupina"),
    ("lab_group", "Lab. skupina"),
    ("classification", "Klasifikace"),
]
DATE_KEYS = {"measurement_date", "submission_date"}
PREVIEW_WIDTH = 760


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Razítko – laboratorní cvičení z fyziky")
        self.tasks = load_tasks()
        self.vars = {}
        self._pending = None
        self._photo = None

        form = ttk.Frame(self, padding=10)
        form.grid(row=0, column=0, sticky="nsew")
        preview = ttk.Frame(self, padding=10)
        preview.grid(row=0, column=1, sticky="nsew")
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        row = 0
        for key, label in TEXT_FIELDS:
            ttk.Label(form, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = self.vars[key] = tk.StringVar()
            ttk.Entry(form, textvariable=var, width=34).grid(row=row, column=1, sticky="ew", pady=2)
            if key in DATE_KEYS:
                ttk.Button(form, text="Dnes", width=6,
                           command=lambda v=var: v.set(today_str())).grid(row=row, column=2, padx=(4, 0))
            row += 1

        ttk.Separator(form).grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        row += 1

        ttk.Label(form, text="Semestr").grid(row=row, column=0, sticky="w", pady=2)
        self.vars["semester"] = tk.StringVar()
        self.sem_box = ttk.Combobox(form, textvariable=self.vars["semester"], width=8,
                                    values=sorted(self.tasks, key=sort_key))
        self.sem_box.grid(row=row, column=1, sticky="w", pady=2)
        self.sem_box.bind("<<ComboboxSelected>>", lambda e: self.on_semester())
        row += 1

        ttk.Label(form, text="Úloha ze seznamu").grid(row=row, column=0, sticky="w", pady=2)
        self.task_box = ttk.Combobox(form, width=34, state="readonly")
        self.task_box.grid(row=row, column=1, columnspan=2, sticky="ew", pady=2)
        self.task_box.bind("<<ComboboxSelected>>", lambda e: self.on_task_pick())
        row += 1

        ttk.Label(form, text="Číslo úlohy").grid(row=row, column=0, sticky="w", pady=2)
        self.vars["task_number"] = tk.StringVar()
        ttk.Entry(form, textvariable=self.vars["task_number"], width=8).grid(row=row, column=1, sticky="w", pady=2)
        row += 1

        ttk.Label(form, text="Název úlohy").grid(row=row, column=0, sticky="nw", pady=2)
        self.vars["task_name"] = tk.StringVar()
        ttk.Entry(form, textvariable=self.vars["task_name"], width=34).grid(
            row=row, column=1, columnspan=2, sticky="ew", pady=2)
        row += 1

        ttk.Label(form, text="Prázdné datum odevzdání = dnes, prázdný stud. rok = dopočítá se.",
                  foreground="gray", wraplength=300).grid(row=row, column=0, columnspan=3, sticky="w", pady=(8, 0))
        row += 1

        buttons = ttk.Frame(form)
        buttons.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(buttons, text="Uložit PNG…", command=self.save_png).pack(side="left")
        ttk.Button(buttons, text="Uložit data.json", command=self.save_json).pack(side="left", padx=6)

        self.preview_label = ttk.Label(preview)
        self.preview_label.pack(anchor="n")
        self.status = ttk.Label(preview, foreground="gray")
        self.status.pack(anchor="w", pady=(6, 0))

        self.load(DATA if DATA.exists() else EXAMPLE)
        for var in self.vars.values():
            var.trace_add("write", lambda *_: self.schedule_preview())
        self.update_preview()

    # ---- data ----
    def load(self, path: Path):
        data = {}
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except ValueError as e:
                messagebox.showwarning("Chyba", f"{path.name} nelze načíst: {e}")
        for key, var in self.vars.items():
            var.set(str(data.get(key, "")))
        self.refresh_task_list()

    def data(self) -> dict:
        return {k: v.get() for k, v in self.vars.items()}

    # ---- semester / task picking ----
    def refresh_task_list(self):
        sem = self.tasks.get(self.vars["semester"].get().strip(), {})
        items = [f"{n} – {name}" for n, name in sorted(sem.items(), key=lambda kv: sort_key(kv[0]))]
        self.task_box["values"] = items
        current = self.vars["task_number"].get().strip()
        match = next((i for i in items if i.split(" – ", 1)[0] == current), "")
        self.task_box.set(match)

    def on_semester(self):
        self.refresh_task_list()

    def on_task_pick(self):
        num, name = self.task_box.get().split(" – ", 1)
        self.vars["task_number"].set(num.rstrip("b"))   # "8b" alternative is still task 8
        self.vars["task_name"].set(name)

    # ---- preview / saving ----
    def schedule_preview(self):
        if self._pending:
            self.after_cancel(self._pending)
        self._pending = self.after(250, self.update_preview)

    def update_preview(self):
        self._pending = None
        img = render_stamp(IMAGE, fill_defaults(self.data(), warn=False), scale=2)
        h = round(img.height * PREVIEW_WIDTH / img.width)
        self._photo = ImageTk.PhotoImage(img.resize((PREVIEW_WIDTH, h)))
        self.preview_label.configure(image=self._photo)

    def save_png(self):
        path = filedialog.asksaveasfilename(
            initialdir=HERE, initialfile="razitko_filled.png",
            defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            render_stamp(IMAGE, fill_defaults(self.data(), warn=False)).save(path)
        except OSError as e:
            messagebox.showerror("Chyba", f"Nelze uložit {path}:\n{e}\n\nNení soubor otevřený v jiném programu?")
            return
        self.status.configure(text=f"Uloženo: {path}")

    def save_json(self):
        DATA.write_text(json.dumps(self.data(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.status.configure(text=f"Uloženo: {DATA}")


def today_str() -> str:
    t = date.today()
    return DATE_FMT.format(d=t.day, m=t.month, y=t.year)


def sort_key(s: str):
    digits = "".join(c for c in s if c.isdigit())
    return (int(digits) if digits else 0, s)


if __name__ == "__main__":
    App().mainloop()
