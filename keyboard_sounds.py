import os
import random
import re
import tkinter as tk
from tkinter import messagebox

try:
    import winsound

    def play_sound(path: str) -> None:
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC)
except ImportError:  # non-Windows fallback
    try:
        from playsound import playsound as play_sound  # type: ignore
    except Exception:  # playsound not installed
        def play_sound(path: str) -> None:
            pass


class SoundMapper:
    """Load and provide random sound pairs for different key categories."""

    def __init__(self, sound_dir: str = "sounds") -> None:
        self.sound_dir = sound_dir
        self.sounds = {
            "space": [],
            "modifier": [],
            "basic": [],
        }
        self._load_sounds()

    _PATTERN = re.compile(r"(A2-|audio-)(\d+)\.wav$", re.IGNORECASE)

    def _load_sounds(self) -> None:
        for name in os.listdir(self.sound_dir):
            match = self._PATTERN.match(name)
            if not match:
                continue
            prefix, digits = match.groups()
            num = int(digits)
            if num % 2 == 0:  # expect odd numbers only for down sounds
                continue
            even_digits = str(num + 1).zfill(len(digits))
            pair_name = f"{prefix}{even_digits}.wav"
            pair_path = os.path.join(self.sound_dir, pair_name)
            if not os.path.exists(pair_path):
                continue
            path = os.path.join(self.sound_dir, name)
            pair = (path, pair_path)
            if prefix.lower().startswith("a2-"):
                if 1 <= num <= 8:
                    self.sounds["space"].append(pair)
                else:
                    self.sounds["modifier"].append(pair)
            else:  # audio-
                self.sounds["basic"].append(pair)

    def get_random_pair(self, category: str):
        pool = self.sounds.get(category)
        if not pool:
            return None
        return random.choice(pool)


class KeyNoiseApp(tk.Tk):
    """Main application window."""

    def __init__(self, sound_dir: str = "sounds") -> None:
        super().__init__()
        self.title("Keyboard Noises")
        self.geometry("300x100")
        self.label = tk.Label(self, text="Press keys to hear sounds")
        self.label.pack(expand=True)
        self.mapper = SoundMapper(sound_dir)
        self.pressed = {}
        self.bind_all("<KeyPress>", self._on_press)
        self.bind_all("<KeyRelease>", self._on_release)

    MODIFIERS = {
        "Return",
        "BackSpace",
        "Shift_L",
        "Shift_R",
        "Control_L",
        "Control_R",
        "Alt_L",
        "Alt_R",
        "Caps_Lock",
    }

    def _category(self, keysym: str) -> str:
        if keysym == "space":
            return "space"
        if keysym in self.MODIFIERS:
            return "modifier"
        return "basic"

    def _play(self, path: str) -> None:
        if not os.path.exists(path):
            messagebox.showerror("Missing sound", f"{path} not found")
            return
        play_sound(path)

    def _on_press(self, event: tk.Event) -> None:
        category = self._category(event.keysym)
        pair = self.mapper.get_random_pair(category)
        if pair is None:
            return
        self.pressed[event.keysym] = pair
        self._play(pair[0])

    def _on_release(self, event: tk.Event) -> None:
        pair = self.pressed.pop(event.keysym, None)
        if pair:
            self._play(pair[1])


if __name__ == "__main__":
    app = KeyNoiseApp()
    app.mainloop()
