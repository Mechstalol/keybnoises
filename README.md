work
Yah im just coding and shi

# Keyboard Noises

This project contains a small Python application that plays a sound whenever a key is pressed in the window.

## Structure
- `keyboard_sounds.py` – main application.

## Running
1. Ensure Python 3 is installed on Windows.
2. Place your sound files in the `sounds` folder.
3. Run the application:
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
