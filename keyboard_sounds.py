import os
import random
import re
import tkinter as tk
from tkinter import messagebox

# Try winsound on Windows; otherwise fall back to playsound or no-op
try:
    import winsound
    def play_sound(path: str) -> None:
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
except ImportError:
    try:
        from playsound import playsound as play_sound  # type: ignore
    except ImportError:
        def play_sound(path: str) -> None:
            pass

# If you prefer pygame for playback and a dropdown UI, you can
# swap in the pygame code below—otherwise the winsound/playsound 
# logic above will work cross-platform.

# Uncomment if you want to use pygame:
# import pygame
# pygame.mixer.init()

class SoundMapper:
    """Load and provide random sound pairs for different key categories."""
    _PATTERN = re.compile(r"(A2-|audio-)(\d+)\.wav$", re.IGNORECASE)

    def __init__(self, sound_dir: str = "sounds") -> None:
        self.sound_dir = sound_dir
        self.sounds = {"space": [], "modifier": [], "basic": []}
        self._load_sounds()

    def _load_sounds(self) -> None:
        for name in os.listdir(self.sound_dir):
            match = self._PATTERN.match(name)
            if not match:
                continue
            prefix, digits = match.groups()
            num = int(digits)
            if num % 2 == 0:  # only odd (key-down) files here
                continue

            even_digits = str(num + 1).zfill(len(digits))
            down = os.path.join(self.sound_dir, name)
            up   = os.path.join(self.sound_dir, f"{prefix}{even_digits}.wav")
            if not os.path.exists(up):
                continue

            key = (
                "space"    if prefix.lower().startswith("a2-") and 1 <= num <= 8 else
                "modifier" if prefix.lower().startswith("a2-") else
                "basic"
            )
            self.sounds[key].append((down, up))

    def get_random_pair(self, category: str):
        pool = self.sounds.get(category, [])
        return random.choice(pool) if pool else None


class KeyNoiseApp(tk.Tk):
    """Main application window."""

    MODIFIERS = {
        "Return", "BackSpace", "Shift_L", "Shift_R",
        "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock",
    }

    def __init__(self, sound_dir: str = "sounds") -> None:
        super().__init__()
        self.sound_dir = sound_dir
        self.title("Keyboard Noises")
        self.geometry("300x100")
        self.label = tk.Label(self, text="Press keys to hear sounds")
        self.label.pack(expand=True)

        self.mapper = SoundMapper(sound_dir)
        self.pressed = {}
        self.bind_all("<KeyPress>",   self._on_press)
        self.bind_all("<KeyRelease>", self._on_release)

    def _category(self, keysym: str) -> str:
        if keysym == "space":
            return "space"
        if keysym in self.MODIFIERS:
            return "modifier"
        return "basic"

    def _play(self, path: str) -> None:
        if not os.path.exists(path):
            messagebox.showerror("Missing sound", f"{path} not found")
        else:
            play_sound(path)
            # If you uncommented pygame above, use:
            # pygame.mixer.music.load(path)
            # pygame.mixer.music.play()

    def _on_press(self, event: tk.Event) -> None:
        pair = self.mapper.get_random_pair(self._category(event.keysym))
        if pair:
            self.pressed[event.keysym] = pair
            self._play(pair[0])

    def _on_release(self, event: tk.Event) -> None:
        pair = self.pressed.pop(event.keysym, None)
        if pair:
            self._play(pair[1])


if __name__ == "__main__":
    app = KeyNoiseApp()
    app.mainloop()
