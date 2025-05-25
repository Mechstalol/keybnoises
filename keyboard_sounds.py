import os
import random
import re
import tkinter as tk
from tkinter import messagebox

# Cross-platform sound playback: winsound on Windows, playsound fallback elsewhere
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

class SoundMapper:
    """Load and categorize WAV file pairs for space, modifier, and basic key sounds."""

    def __init__(self, sound_dir: str = "sounds") -> None:
        self.sound_dir = sound_dir
        # Each category holds a list of (down_path, up_path) pairs
        self.sounds = {"space": [], "modifier": [], "basic": []}
        self._load_sounds()

    def _load_sounds(self) -> None:
        for name in os.listdir(self.sound_dir):
            if not name.lower().endswith(".wav"):
                continue
            lower = name.lower()
            # Find the ID substring "a2-XXXX" or "audio-XXXX" anywhere
            m = re.search(r"(a2|audio)-(\d+)", lower)
            if not m:
                continue
            prefix_type, digits = m.group(1), m.group(2)
            num = int(digits)
            # Only odd-numbered files are 'down' sounds
            if num % 2 == 0:
                continue

            # Build partner filename: same prefix_text + next even ID + suffix_text
            start, end = m.span(0)
            prefix_text = name[:start]
            suffix_text = name[end:]
            next_id = str(num + 1).zfill(len(digits))
            partner_id = f"{prefix_type}-{next_id}"
            down_path = os.path.join(self.sound_dir, name)
            up_name = f"{prefix_text}{partner_id}{suffix_text}"
            up_path = os.path.join(self.sound_dir, up_name)
            if not os.path.exists(up_path):
                continue

            # Determine category
            if lower.startswith("audio ") or prefix_type == "audio":
                cat = "basic"
            else:
                # prefix_type == "a2"
                cat = "space" if 1 <= num <= 8 else "modifier"

            self.sounds[cat].append((down_path, up_path))

        # Shuffle pairs within each category for randomness
        for pairs in self.sounds.values():
            random.shuffle(pairs)

    def get_random_pair(self, category: str):
        pool = self.sounds.get(category, [])
        return random.choice(pool) if pool else None

class KeyNoiseApp(tk.Tk):
    """Main application window with proper pairing for key-down and key-up."""

    MODIFIERS = {
        "Return", "BackSpace", "Shift_L", "Shift_R",
        "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock",
    }

    def __init__(self, sound_dir: str = "sounds") -> None:
        super().__init__()
        self.sound_dir = sound_dir
        self.title("Keyboard Noises")
        self.geometry("400x200")

        tk.Label(self, text="Press keys to hear sounds", font=("Segoe UI", 12)).pack(pady=10)
        self.status = tk.Label(self, text="Loading sounds...", anchor="w")
        self.status.pack(fill="x", side="bottom")

        self.pressed = {}  # track which keysyms have an active pair
        try:
            self.mapper = SoundMapper(sound_dir)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sounds: {e}")
            self.destroy()
            return

        sc = len(self.mapper.sounds["space"])
        mc = len(self.mapper.sounds["modifier"])
        bc = len(self.mapper.sounds["basic"])
        self.status.config(text=f"Loaded: space={sc}, modifier={mc}, basic={bc}")

        self.bind_all("<KeyPress>", self._on_press)
        self.bind_all("<KeyRelease>", self._on_release)

    def _category(self, keysym: str) -> str:
        if keysym == "space":
            return "space"
        if keysym in self.MODIFIERS:
            return "modifier"
        return "basic"

    def _play(self, path: str) -> None:
        self.status.config(text=f"Playing: {os.path.basename(path)}")
        if not os.path.exists(path):
            messagebox.showerror("Missing sound", f"{path} not found")
        else:
            play_sound(path)

    def _on_press(self, event: tk.Event) -> None:
        # Prevent retriggering while held
        if event.keysym in self.pressed:
            return

        cat = self._category(event.keysym)
        pair = self.mapper.get_random_pair(cat)
        if not pair:
            self.status.config(text=f"No {cat} sounds available")
            return

        self.pressed[event.keysym] = pair
        down_path, _ = pair
        self._play(down_path)

    def _on_release(self, event: tk.Event) -> None:
        pair = self.pressed.pop(event.keysym, None)
        if pair:
            _, up_path = pair
            self._play(up_path)
            self.status.config(text=f"Key released: {event.keysym}")

if __name__ == "__main__":
    app = KeyNoiseApp()
    app.mainloop()
