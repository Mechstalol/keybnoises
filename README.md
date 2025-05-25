# Keyboard Noises

This project contains a small Python application that plays keyboard sounds whenever a key is pressed.
The window lets you choose from any `.wav` files in the `sounds` folder, adjust the volume, and shows "Made by mechsta" at the bottom.

## Structure
- `keyboard_sounds.py` – main application.
- `sounds/` – directory for your `.wav` files. Any files placed here will appear in the application's drop-down menu.

## Running
1. Ensure Python 3 is installed on Windows.
2. Install dependencies:
   ```bash
   pip install pygame
   ```
3. Place your `.wav` files in the `sounds` folder.
4. Run the application:
   ```bash
   python keyboard_sounds.py
   ```

## Building an EXE
You can build a standalone Windows executable with `pyinstaller`:
```bash
pip install pyinstaller
pyinstaller --onefile keyboard_sounds.py
```
The generated EXE will appear in the `dist` directory.
