# Keyboard Noises

This project contains a small Python application that plays a sound whenever a key is pressed in the window.

## Structure
- `keyboard_sounds.py` – main application.
- `sounds/` – directory for the sound files used by the application.

### Sound file naming
The application groups sound files into pools based on their filename:

- Files starting with `audio-` are for **regular keys**.
- Files starting with `A2-` with numbers **1-8** are for the **spacebar**.
- Other `A2-` files are for **modifier** keys like Enter, Backspace and Shift.

Within each group, odd-numbered files are played on key press and the next even
number is played on key release. For example `audio-0001.wav` is paired with
`audio-0002.wav`.


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
