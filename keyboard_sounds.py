import os
import random
import re
import threading
import tkinter as tk
from tkinter import messagebox

import pygame
import numpy as np
from pynput.keyboard import Key, Listener

# ─────────────────────────────────────────────────────────────────────────────
# Initialize pygame (including the mixer). Let SDL/pygame pick however many channels.
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
        self.base_dir = base_sound_dir
        self.profiles = self._find_profiles()
        self.current = None
        # Three lists: self.sounds["space"], ["modifier"], ["basic"]
        # Each element is a tuple (down_array, up_array) of shape (N, mixer_channels), dtype=int16.
        self.sounds = {"space": [], "modifier": [], "basic": []}

    def _find_profiles(self):
        """
        Return a sorted list of all subfolders under self.base_dir
        (each one is treated as a “profile”).
        """
        out = []
        if not os.path.isdir(self.base_dir):
            return out
        for entry in os.listdir(self.base_dir):
            full = os.path.join(self.base_dir, entry)
            if os.path.isdir(full):
                out.append(entry)
        return sorted(out)

    def load_profile(self, profile_name):
        """
        Clear previous lists and load all matching down/up pairs
        from self.base_dir/profile_name. Store each pair as (down_array, up_array).
        """
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

            # Match only “down” patterns
            m = re.match(r'^(SpaceDown|NrmlKeyDown|SpclKeyDown)_(\d+)\.wav$', fname, re.IGNORECASE)
            if not m:
                print(f"[DEBUG] No down-match for: {fname}")
                continue

            down_tag = m.group(1)  # e.g. "SpaceDown"
            idx = m.group(2)       # e.g. "001"
            tag_lower = down_tag.lower()

            if tag_lower.startswith("spacedown"):
                cat = "space"
            elif tag_lower.startswith("nrmlkeydown"):
                cat = "basic"
            elif tag_lower.startswith("spclkeydown"):
                cat = "modifier"
            else:
                cat = "basic"

            # Skip duplicate IDs within same category
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

            # Load each WAV as a pygame.mixer.Sound so we can grab its raw samples
            try:
                raw_down = pygame.mixer.Sound(down_path)
                raw_up = pygame.mixer.Sound(up_path)
            except pygame.error as e:
                print(f"[DEBUG] Failed to load {down_path} or {up_path}: {e}")
                continue

            # Convert each to a NumPy array
            arr_down = pygame.sndarray.array(raw_down)
            arr_up = pygame.sndarray.array(raw_up)

            print(f"[DEBUG] RAW array for {fname}:    shape={arr_down.shape}, dtype={arr_down.dtype}")
            print(f"[DEBUG] RAW array for {up_name}:  shape={arr_up.shape},   dtype={arr_up.dtype}")

            # Collapse to mono then tile across mixer_channels
            try:
                down_arr_final = self._collapse_and_tile(arr_down)
                up_arr_final = self._collapse_and_tile(arr_up)
            except Exception as ex:
                print(f"[DEBUG] Error converting {fname}/{up_name} to {mixer_channels}ch: {ex}")
                continue

            print(f"[DEBUG] Pair matched (category={cat}): {fname} ↔ {up_name}")
            self.sounds[cat].append((down_arr_final, up_arr_final))

        # Shuffle each category’s list so get_random_pair() is randomized
        for pool in self.sounds.values():
            random.shuffle(pool)

        print(
            f"[DEBUG] Final pool sizes (profile='{profile_name}'): "
            f"space={len(self.sounds['space'])}, "
            f"modifier={len(self.sounds['modifier'])}, "
            f"basic={len(self.sounds['basic'])}\n"
        )

    def _collapse_and_tile(self, arr: np.ndarray) -> np.ndarray:
        """
        1) If arr.ndim == 1, it’s already mono (shape (N,))  
           If arr.ndim == 2 with shape (N, C_original), average across axis=1 → (N,)  
        2) Tile that mono array across exactly mixer_channels → (N, mixer_channels)  
        3) Return a dtype=int16 array
        """
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
        """
        Return one random (down_arr, up_arr) tuple for the given category:
        “space”, “modifier”, or “basic”. Each arr is a NumPy array (N, mixer_channels).
        Returns None if that category is empty.
        """
        pool = self.sounds.get(category, [])
        return random.choice(pool) if pool else None


class KeyNoiseApp(tk.Tk):
    """
    Main application window:
      - Dropdown to pick any profile folder under ./sounds/
      - Volume slider (0 → 1) which we map to actual gain (0 → 2× old)
      - Global key listener (via pynput) so sounds play even if this window is unfocused
      - Polyphonic keydown + keyup playback, each multiplied by the chosen gain factor
    """

    # Define the same modifier “keysym” set we used before:
    MODIFIERS = {
        "Return", "BackSpace", "Shift_L", "Shift_R",
        "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock"
    }

    def __init__(self, base_sound_dir="sounds"):
        super().__init__()
        self.title("Keyboard Noises (Global Listener + Adjustable Volume)")
        self.geometry("550x350")

        # 1) Instantiate the mapper and find all profiles
        self.mapper = SoundMapper(base_sound_dir)
        if not self.mapper.profiles:
            messagebox.showerror("Error", "No sound profiles found under 'sounds/'")
            self.destroy()
            return

        # 2) Dropdown: choose a profile folder
        self.active_profile = tk.StringVar(value=self.mapper.profiles[0])
        tk.Label(self, text="Select Profile:", font=("Segoe UI", 10)).pack(pady=(10, 0))
        self.profile_menu = tk.OptionMenu(
            self, self.active_profile, *self.mapper.profiles, command=self._on_profile_change
        )
        self.profile_menu.pack(pady=5)

        # 3) Volume slider: value in [0.0, 1.0], default = 0.5 → “old default loudness”
        #    We map slider_value → actual_gain = slider_value * 2.0
        tk.Label(self, text="Volume (0 → 2× old):", font=("Segoe UI", 10)).pack(pady=(15, 0))
        self.volume = tk.DoubleVar(value=0.5)
        self.vol_slider = tk.Scale(
            self,
            from_=0.0,
            to=1.0,
            resolution=0.01,
            orient="horizontal",
            variable=self.volume,
            length=400,
            label="Slider maps to ×2 gain",
            command=self._on_volume_change  # update self.gain_factor each move
        )
        self.vol_slider.pack()
        # Initialize gain_factor = 0.5 * 2 = 1.0 (the “old default” volume)
        self.gain_factor = float(self.volume.get()) * 2.0

        # 4) Status bar at the bottom
        self.status = tk.Label(self, text="Loading profile…", anchor="w")
        self.status.pack(fill="x", side="bottom")

        # 5) Load the default (first) profile
        self.mapper.load_profile(self.active_profile.get())
        sc = len(self.mapper.sounds["space"])
        mc = len(self.mapper.sounds["modifier"])
        bc = len(self.mapper.sounds["basic"])
        self.status.config(
            text=f"Loaded '{self.active_profile.get()}': space={sc}, modifier={mc}, basic={bc}"
        )

        # 6) Tracks which keys are currently pressed
        #     Key: pynput key object, Value: the “up” NumPy array to play
        self.pressed = {}

        # 7) Start global listener in a background thread
        listener = Listener(on_press=self._on_global_key_press,
                            on_release=self._on_global_key_release,
                            suppress=False)
        listener.daemon = True   # so that it does not block program exit
        listener.start()

    def _on_volume_change(self, val):
        """
        Called in the Tkinter main thread whenever the slider moves.
        Update self.gain_factor = slider_value * 2.0
        """
        try:
            v = float(val)
        except ValueError:
            v = 0.0
        self.gain_factor = v * 2.0

    def _on_profile_change(self, new_profile):
        """
        Called when the user selects a new profile from the dropdown.
        Reload that folder’s sounds, update status, clear any held keys.
        """
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
        """
        Convert a pynput.keyboard.Key or KeyCode into the same 'keysym' strings
        our code uses for categorization:

          Key.space      → 'space'
          Key.enter      → 'Return'
          Key.backspace  → 'BackSpace'
          Key.shift / shift_l / shift_r → 'Shift_L' / 'Shift_R'
          Key.ctrl / ctrl_l / ctrl_r     → 'Control_L' / 'Control_R'
          Key.alt / alt_l / alt_r        → 'Alt_L' / 'Alt_R'
          Key.caps_lock   → 'Caps_Lock'
          Otherwise, for any single character KeyCode, treat as 'basic'
        """
        # If it's a special Key enum, handle directly
        if key == Key.space:
            return "space"
        if key == Key.enter:
            return "Return"
        if key == Key.backspace:
            return "BackSpace"

        # Shift / Ctrl / Alt / Caps Lock
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

        # Otherwise, if it's a normal character KeyCode, return its char
        # The code will treat anything not in MODIFIERS or not exactly 'space'
        # as category="basic".
        try:
            char = key.char
            if char is not None:
                return char
        except AttributeError:
            pass

        # If all else fails, return "" → category will become "basic"
        return ""

    def _category(self, keysym: str) -> str:
        """
        Exactly the same logic as before:
           - If keysym == "space", category = "space"
           - If keysym in MODIFIERS, category = "modifier"
           - Otherwise, category = "basic"
        """
        if keysym == "space":
            return "space"
        if keysym in self.MODIFIERS:
            return "modifier"
        return "basic"

    def _on_global_key_press(self, key):
        """
        Called by pynput.Listener when any key is pressed anywhere on the system.
        We map that to a category, pick a random down/up pair, multiply by current gain,
        convert to a Sound, and play. We also record the 'up_array' so we can play it
        on release.
        """
        # Prevent auto-repeat: if key is already in self.pressed, skip
        if key in self.pressed:
            return

        # Map pynput key to our keysym
        keysym = self._map_pynput_key_to_keysym(key)
        cat = self._category(keysym)

        pair = self.mapper.get_random_pair(cat)
        if not pair:
            # No sounds available in that category
            return

        down_arr, up_arr = pair

        # Apply gain: gain_factor ∈ [0, 2.0]
        gain = self.gain_factor
        clipped = np.clip((down_arr.astype(np.int32) * gain), -32768, 32767).astype(np.int16)

        try:
            snd = pygame.sndarray.make_sound(clipped)
            ch = snd.play()
            if ch:
                ch.set_volume(1.0)  # we baked gain into samples already
        except Exception as e:
            print(f"[DEBUG] Error playing down sound with gain {gain:.2f}: {e}")

        # Store the array for the up event
        self.pressed[key] = up_arr

        # Update the status in the GUI thread
        self.status.after(0, lambda: self.status.config(text=f"Down: {keysym} (gain={gain:.2f})"))

    def _on_global_key_release(self, key):
        """
        Called by pynput.Listener when any key is released. We look up the stored
        up_array, apply the same gain, play that sound, and remove from self.pressed.
        """
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

        # Update the status in the GUI thread
        self.status.after(0, lambda: self.status.config(text=f"Up (gain={gain:.2f})"))


if __name__ == "__main__":
    app = KeyNoiseApp(base_sound_dir="sounds")
    app.mainloop()
