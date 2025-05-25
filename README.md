yty24d-codex/create-windows-app-to-play-keyboard-noises


## Running
1. Ensure Python 3 is installed on Windows.
2. Place your sound files in the `sounds` folder.
3. Run the application:
   ```bash
   python keyboard_sounds.py
   ```
   If a requested WAV file is missing, the app now shows an error message
   using `tk.messagebox.showerror`.

main
## Building an EXE
You can build a standalone Windows executable with `pyinstaller`:
```bash
pip install pyinstaller
pyinstaller --onefile keyboard_sounds.py
```
The generated EXE will appear in the `dist` directory.

## License
This project is released under the [MIT License](LICENSE).
