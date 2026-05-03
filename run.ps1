$env:PYTHON_GIL = "1"
& "$PSScriptRoot\.venv\Scripts\python.exe" -m gui.main @args
