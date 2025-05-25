import os
import random
import re
import tkinter as tk
from tkinter import messagebox
import pygame

# Initialize pygame mixer for polyphonic playback
pygame.mixer.init()

class SoundMapper:
    """Load and categorize WAV file pairs for space, modifier, and basic key sounds using pygame."""

    def __init__(self, sound_dir: str = "sounds") -> None:
        self.sound_dir = sound_dir
        # Each category holds a list of (down_sound, up_sound) pygame Sound objects
        self.sounds = {"space": [], "modifier": [], "basic": []}
        self._load_sounds()

    def _load_sounds(self) -> None:
        for fname in os.listdir(self.sound_dir):
            if not fname.lower().endswith(".wav"):
                continue
            lower = fname.lower()
            # Find ID substring "a2-XXXX" or "audio-XXXX" anywhere
            m = re.search(r"(a2|audio)-(\d+)", lower)
            if not m:
                continue
            kind, digits = m.group(1), m.group(2)
            num = int(digits)
            # Only odd numbered files are 'down' sounds
            if num % 2 == 0:
                continue

            # Build partner filename for the 'up' sound by incrementing the ID
            start, end = m.span(0)
            prefix_text = fname[:start]
            suffix_text = fname[end:]
            next_id = str(num + 1).zfill(len(digits))
            up_tag = f"{kind}-{next_id}"
            down_path = os.path.join(self.sound_dir, fname)
            up_name = f"{prefix_text}{up_tag}{suffix_text}"
            up_path = os.path.join(self.sound_dir, up_name)
            if not os.path.exists(up_path):
                continue

            # Load sounds into pygame Sound objects
            down_sound = pygame.mixer.Sound(down_path)
            up_sound   = pygame.mixer.Sound(up_path)

            # Determine category
            if lower.startswith("audio ") or kind == "audio":
                cat = "basic"
            else:
                # kind == "a2"
                cat = "space" if 1 <= num <= 8 else "modifier"

            self.sounds[cat].append((down_sound, up_sound))

        # Shuffle pairs for randomness
        for pool in self.sounds.values():
            random.shuffle(pool)

    def get_random_pair(self, category: str):
        pool = self.sounds.get(category, [])
        return random.choice(pool) if pool else None

class KeyNoiseApp(tk.Tk):
    """Main application window with polyphonic keydown/keyup sounds."""

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

        # Track keys currently pressed to prevent repeats
        self.pressed = {}
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

        # Bind key events
        self.bind_all("<KeyPress>",   self._on_press)
        self.bind_all("<KeyRelease>", self._on_release)

    def _category(self, keysym: str) -> str:
        if keysym == "space":
            return "space"
        if keysym in self.MODIFIERS:
            return "modifier"
        return "basic"

    def _on_press(self, event: tk.Event) -> None:
        # Ignore auto-repeat for held keys
        if event.keysym in self.pressed:
            return

        cat = self._category(event.keysym)
        pair = self.mapper.get_random_pair(cat)
        if not pair:
            self.status.config(text=f"No {cat} sounds available")
            return

        down_sound, up_sound = pair
        self.pressed[event.keysym] = up_sound
        down_sound.play()
        self.status.config(text=f"Down: {event.keysym}")

    def _on_release(self, event: tk.Event) -> None:
        up_sound = self.pressed.pop(event.keysym, None)
        if up_sound:
            up_sound.play()
            self.status.config(text=f"Up: {event.keysym}")

if __name__ == "__main__":
    app = KeyNoiseApp()
    app.mainloop()
