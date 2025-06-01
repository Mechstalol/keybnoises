import sys
import os
import random
import re
import tkinter as tk
from tkinter import messagebox

import pygame
import numpy as np
from pynput.keyboard import Key, Listener

# ─────────────────────────────────────────────────────────────────────────────
def resource_path(relative_path):
    """
    Return the absolute path to a resource in development (relative to project root)
    or to the bundled resource when frozen by PyInstaller (inside _MEIPASS).
    """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)
# ─────────────────────────────────────────────────────────────────────────────

# Initialize pygame (including mixer). Let SDL/pygame pick however many channels.
pygame.init()
mixer_info = pygame.mixer.get_init()
if mixer_info is None:
    raise RuntimeError("Failed to initialize pygame mixer")

mixer_freq, mixer_size, mixer_channels = mixer_info
print(f"\n[DEBUG] pygame mixer initialized with: frequency={mixer_freq}, size={mixer_size}, channels={mixer_channels}")
# ─────────────────────────────────────────────────────────────────────────────

class SoundMapper:
    """
    - Scans a subfolder (e.g. 'gmk87_vertexv1-lubed') under ./sounds/ for:
         SpaceDown_###.wav ↔ SpaceUp_###.wav   → category "space"
         NrmlKeyDown_###.wav ↔ NrmlKeyUp_###.wav → category "basic"
         SpclKeyDown_###.wav ↔ SpclKeyUp_###.wav → category "modifier"
    - For each WAV (no matter how many channels it originally has), it:
       1) Reads it into a NumPy array via pygame.sndarray.array(...)
       2) Averages across all original channels → a mono array (length N)
       3) Tiles that mono array across exactly mixer_channels → shape (N, mixer_channels)
       4) Stores that final NumPy array (dtype=int16) for later playback.
    """

    def __init__(self, base_sound_dir="sounds"):
        # Use resource_path so when frozen it points inside _MEIPASS
        self.base_dir = resource_path(base_sound_dir)
        self.profiles = self._find_profiles()
        self.current = None
        self.sounds = {"space": [], "modifier": [], "basic": []}

    def _find_profiles(self):
        out = []
        if not os.path.isdir(self.base_dir):
            return out
        for entry in os.listdir(self.base_dir):
            full = os.path.join(self.base_dir, entry)
            if os.path.isdir(full):
                out.append(entry)
        return sorted(out)

    def load_profile(self, profile_name):
        self.current = profile_name
        prof_folder = os.path.join(self.base_dir, profile_name)

        # Reset pools
        self.sounds = {"space": [], "modifier": [], "basic": []}
        seen_ids = {"space": set(), "modifier": set(), "basic": set()}

        print(f"\n[DEBUG] Loading profile '{profile_name}' from: {prof_folder}")
        try:
            all_files = os.listdir(prof_folder)
        except FileNotFoundError:
            print(f"[DEBUG] Folder not found: {prof_folder}")
            return

        print("[DEBUG] Files found:", all_files)

        for fname in all_files:
            if not fname.lower().endswith(".wav"):
                print(f"[DEBUG] Skipping (not .wav): {fname}")
                continue

            m = re.match(r'^(SpaceDown|NrmlKeyDown|SpclKeyDown)_(\d+)\.wav$', fname, re.IGNORECASE)
            if not m:
                print(f"[DEBUG] No down-match for: {fname}")
                continue

            down_tag = m.group(1)   # e.g. "SpaceDown"
            idx = m.group(2)        # e.g. "001"
            tag_lower = down_tag.lower()

            if tag_lower.startswith("spacedown"):
                cat = "space"
            elif tag_lower.startswith("nrmlkeydown"):
                cat = "basic"
            elif tag_lower.startswith("spclkeydown"):
                cat = "modifier"
            else:
                cat = "basic"

            if idx in seen_ids[cat]:
                print(f"[DEBUG] Already saw {cat}-ID {idx}, skipping {fname}")
                continue
            seen_ids[cat].add(idx)

            up_tag = down_tag.replace("Down", "Up")
            up_name = f"{up_tag}_{idx}.wav"
            down_path = os.path.join(prof_folder, fname)
            up_path = os.path.join(prof_folder, up_name)

            if not os.path.exists(up_path):
                print(f"[DEBUG] Found DOWN but missing UP: {fname} → (no {up_name})")
                continue

            try:
                raw_down = pygame.mixer.Sound(down_path)
                raw_up = pygame.mixer.Sound(up_path)
            except pygame.error as e:
                print(f"[DEBUG] Failed to load {down_path} or {up_path}: {e}")
                continue

            arr_down = pygame.sndarray.array(raw_down)
            arr_up = pygame.sndarray.array(raw_up)

            print(f"[DEBUG] RAW array for {fname}:    shape={arr_down.shape}, dtype={arr_down.dtype}")
            print(f"[DEBUG] RAW array for {up_name}:  shape={arr_up.shape},   dtype={arr_up.dtype}")

            try:
                down_arr_final = self._collapse_and_tile(arr_down)
                up_arr_final = self._collapse_and_tile(arr_up)
            except Exception as ex:
                print(f"[DEBUG] Error converting {fname}/{up_name} to {mixer_channels}ch: {ex}")
                continue

            print(f"[DEBUG] Pair matched (category={cat}): {fname} ↔ {up_name}")
            self.sounds[cat].append((down_arr_final, up_arr_final))

        for pool in self.sounds.values():
            random.shuffle(pool)

        print(
            f"[DEBUG] Final pool sizes (profile='{profile_name}'): "
            f"space={len(self.sounds['space'])}, "
            f"modifier={len(self.sounds['modifier'])}, "
            f"basic={len(self.sounds['basic'])}\n"
        )

    def _collapse_and_tile(self, arr: np.ndarray) -> np.ndarray:
        if arr.ndim == 1:
            mono = arr
        else:
            C_orig = arr.shape[1]
            if C_orig == 1:
                mono = arr[:, 0]
            else:
                mono = arr.mean(axis=1).astype(arr.dtype)

        tiled = np.tile(mono.reshape(-1, 1), (1, mixer_channels))
        print(f"[DEBUG] Converted to {mixer_channels}ch shape={tiled.shape}, dtype={tiled.dtype}")
        return tiled

    def get_random_pair(self, category: str):
        pool = self.sounds.get(category, [])
        return random.choice(pool) if pool else None


class KeyNoiseApp(tk.Tk):
    """
    Main window:
      - Dropdown to choose a profile
      - Simple “Volume” slider
      - Global key listener (via pynput) so clicks work even if this window isn’t focused
      - Footer “Made by Mechsta”
    """

    MODIFIERS = {
        "Return", "BackSpace", "Shift_L", "Shift_R",
        "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock"
    }

    def __init__(self, base_sound_dir="sounds"):
        super().__init__()
        # Include “Made by Mechsta” in the title
        self.title("Keyboard Noises – Made by Mechsta")
        self.geometry("550x360")

        # 1) SoundMapper, using resource_path
        self.mapper = SoundMapper(base_sound_dir)
        if not self.mapper.profiles:
            messagebox.showerror("Error", "No sound profiles found under 'sounds/'")
            self.destroy()
            return

        # 2) Profile dropdown
        self.active_profile = tk.StringVar(value=self.mapper.profiles[0])
        tk.Label(self, text="Select Profile:", font=("Segoe UI", 10)).pack(pady=(10, 0))
        self.profile_menu = tk.OptionMenu(
            self, self.active_profile, *self.mapper.profiles, command=self._on_profile_change
        )
        self.profile_menu.pack(pady=5)

        # 3) Volume slider (no extra “×2 gain” text—just “Volume”)
        tk.Label(self, text="Volume:", font=("Segoe UI", 10)).pack(pady=(15, 0))
        self.volume = tk.DoubleVar(value=0.5)  # default=0.5 → old default volume
        self.vol_slider = tk.Scale(
            self,
            from_=0.0,
            to=1.0,
            resolution=0.01,
            orient="horizontal",
            variable=self.volume,
            length=400,
            command=self._on_volume_change
        )
        self.vol_slider.pack()
        # Immediately compute gain_factor = slider × 2.0
        self.gain_factor = self.volume.get() * 2.0

        # 4) Status bar
        self.status = tk.Label(self, text="Loading profile…", anchor="w")
        self.status.pack(fill="x", side="bottom")

        # 5) Load default profile
        self.mapper.load_profile(self.active_profile.get())
        sc = len(self.mapper.sounds["space"])
        mc = len(self.mapper.sounds["modifier"])
        bc = len(self.mapper.sounds["basic"])
        self.status.config(
            text=f"Loaded '{self.active_profile.get()}': space={sc}, modifier={mc}, basic={bc}"
        )

        # 6) Track pressed keys
        self.pressed = {}

        # 7) Footer label “Made by Mechsta”
        self.footer = tk.Label(self, text="Made by Mechsta", font=("Segoe UI", 8), fg="gray")
        self.footer.pack(side="bottom", pady=(0, 5))

        # 8) Start global listener (pynput)
        listener = Listener(
            on_press=self._on_global_key_press,
            on_release=self._on_global_key_release,
            suppress=False
        )
        listener.daemon = True
        listener.start()

    def _on_volume_change(self, val):
        """Update gain_factor whenever the slider moves."""
        try:
            v = float(val)
        except ValueError:
            v = 0.0
        self.gain_factor = v * 2.0

    def _on_profile_change(self, new_profile):
        try:
            self.mapper.load_profile(new_profile)
        except Exception as e:
            messagebox.showerror("Profile Error", f"Could not load '{new_profile}': {e}")
            return

        sc = len(self.mapper.sounds["space"])
        mc = len(self.mapper.sounds["modifier"])
        bc = len(self.mapper.sounds["basic"])
        self.status.config(
            text=f"Loaded '{new_profile}': space={sc}, modifier={mc}, basic={bc}"
        )
        self.pressed.clear()

    def _map_pynput_key_to_keysym(self, key) -> str:
        if key == Key.space:
            return "space"
        if key == Key.enter:
            return "Return"
        if key == Key.backspace:
            return "BackSpace"

        if key in (Key.shift, Key.shift_l):
            return "Shift_L"
        if key == Key.shift_r:
            return "Shift_R"
        if key in (Key.ctrl, Key.ctrl_l):
            return "Control_L"
        if key == Key.ctrl_r:
            return "Control_R"
        if key in (Key.alt, Key.alt_l):
            return "Alt_L"
        if key == Key.alt_r:
            return "Alt_R"
        if key == Key.caps_lock:
            return "Caps_Lock"

        try:
            char = key.char
            if char is not None:
                return char
        except AttributeError:
            pass

        return ""

    def _category(self, keysym: str) -> str:
        if keysym == "space":
            return "space"
        if keysym in self.MODIFIERS:
            return "modifier"
        return "basic"

    def _on_global_key_press(self, key):
        if key in self.pressed:
            return

        keysym = self._map_pynput_key_to_keysym(key)
        cat = self._category(keysym)

        pair = self.mapper.get_random_pair(cat)
        if not pair:
            return

        down_arr, up_arr = pair
        gain = self.gain_factor
        clipped = np.clip((down_arr.astype(np.int32) * gain), -32768, 32767).astype(np.int16)

        try:
            snd = pygame.sndarray.make_sound(clipped)
            ch = snd.play()
            if ch:
                ch.set_volume(1.0)
        except Exception as e:
            print(f"[DEBUG] Error playing down sound with gain {gain:.2f}: {e}")

        self.pressed[key] = up_arr
        self.status.after(0, lambda: self.status.config(text=f"Down: {keysym} (gain={gain:.2f})"))

    def _on_global_key_release(self, key):
        up_arr = self.pressed.pop(key, None)
        if up_arr is None:
            return

        gain = self.gain_factor
        clipped = np.clip((up_arr.astype(np.int32) * gain), -32768, 32767).astype(np.int16)

        try:
            snd = pygame.sndarray.make_sound(clipped)
            ch = snd.play()
            if ch:
                ch.set_volume(1.0)
        except Exception as e:
            print(f"[DEBUG] Error playing up sound with gain {gain:.2f}: {e}")

        self.status.after(0, lambda: self.status.config(text=f"Up (gain={gain:.2f})"))


if __name__ == "__main__":
    app = KeyNoiseApp(base_sound_dir="sounds")
    app.mainloop()
