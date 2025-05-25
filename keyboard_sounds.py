import os
import tkinter as tk
from tkinter import messagebox
import winsound

class KeyNoiseApp(tk.Tk):
    def __init__(self, sound_dir="sounds", sound_file="key.wav"):
        super().__init__()
        self.sound_dir = sound_dir
        self.sound_file = sound_file
        self.title("Keyboard Noises")
        self.geometry("300x100")
        self.label = tk.Label(self, text="Press keys to hear sounds")
        self.label.pack(expand=True)
        self.bind_all("<Key>", self._play_sound)

    def _play_sound(self, event):
        path = os.path.join(self.sound_dir, self.sound_file)
        if os.path.exists(path):
            winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            messagebox.showerror("Missing sound", f"{path} not found")

if __name__ == "__main__":
    app = KeyNoiseApp()
    app.mainloop()
