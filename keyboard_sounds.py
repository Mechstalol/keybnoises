import os
import tkinter as tk
from tkinter import messagebox
import pygame

class KeyNoiseApp(tk.Tk):
    def __init__(self, sound_dir="sounds"):
        super().__init__()
        self.sound_dir = sound_dir
        self.sound_files = [f for f in os.listdir(sound_dir) if f.lower().endswith(".wav")]
        self.selected_sound = tk.StringVar(value=self.sound_files[0] if self.sound_files else "")
        self.volume = tk.DoubleVar(value=1.0)

        pygame.mixer.init()

        self.title("Keyboard Noises")
        self.geometry("300x180")

        tk.Label(self, text="Select keyboard sound:").pack(pady=(10, 0))
        self.sound_menu = tk.OptionMenu(self, self.selected_sound, *self.sound_files)
        self.sound_menu.pack()

        tk.Label(self, text="Volume:").pack(pady=(5, 0))
        tk.Scale(self, from_=0, to=1, orient="horizontal", resolution=0.1,
                 variable=self.volume).pack()

        self.status = tk.Label(self, text="Press keys to hear sounds")
        self.status.pack(expand=True)

        tk.Label(self, text="Made by mechsta").pack(side=tk.BOTTOM, pady=5)

        self.bind_all("<Key>", self._play_sound)

    def _play_sound(self, event):
        sound = self.selected_sound.get()
        if not sound:
            return
        path = os.path.join(self.sound_dir, sound)
        if not os.path.exists(path):
            messagebox.showerror("Missing sound", f"{path} not found")
            return

        try:
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(self.volume.get())
            pygame.mixer.music.play()
        except pygame.error as e:
            messagebox.showerror("Playback error", str(e))

if __name__ == "__main__":
    app = KeyNoiseApp()
    app.mainloop()
