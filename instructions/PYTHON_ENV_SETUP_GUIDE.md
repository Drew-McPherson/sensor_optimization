# Python Environment Setup Guide (Beginner Friendly)

This guide helps you run this project on multiple computers **without breaking your Python environment**.

## What is going wrong (plain English)

A Python virtual environment (`.venv`) can break when it is synced across computers (Dropbox, OneDrive, etc.) because:

1. A virtual environment stores machine-specific paths.
2. Those paths are different on each computer.
3. If one computer has a different Python install (or missing install), the synced `.venv` may stop working.

**Important rule:**
- Sync your project files.
- Do **not** sync your working virtual environment between machines.

---

## The safe approach

Create one local environment per computer outside any synced folder.

Suggested placeholders used below:

1. `<repo-path>` = where this repository lives on the current computer.
2. `<venv-path>` = a machine-local virtual environment path such as `C:\venvs\sensor_project`.

Both computers use the same project files, but each computer has its own local Python environment.

---

## Before you start

You need:

1. Python installed on the computer.
2. VS Code installed.
3. This project folder available locally.

---

## Step-by-step setup (do this on each computer)

### Step 1) Open PowerShell

Open a terminal in VS Code or open Windows PowerShell.

### Step 2) Go to the project folder

Run:

```powershell
cd <repo-path>
```

Examples:

1. `cd C:\Projects\sensor_project`
2. `cd D:\work\sensor_project`

### Step 3) Create a machine-local virtual environment (outside Dropbox)

Run:

```powershell
mkdir C:\venvs -ErrorAction SilentlyContinue
python -m venv <venv-path>
```

Why:
- This keeps the environment local to this machine.
- Sync software will not corrupt it.

### Step 4) Activate the environment

Run:

```powershell
<venv-path>\Scripts\Activate.ps1
```

You should now see `(sensor_project)` or similar at the start of your prompt.

### Step 5) Install dependencies

Run:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Why:
- Installs all required libraries into this machine's environment.

### Step 6) Tell VS Code to use this interpreter

In VS Code:

1. Press `Ctrl+Shift+P`.
2. Choose **Python: Select Interpreter**.
3. Select `<venv-path>\Scripts\python.exe`.

Why:
- Ensures editor, terminal, and notebook use the same Python.

### Step 7) Select the same kernel in the notebook

In your notebook:

1. Click the kernel picker (top-right).
2. Choose `<venv-path>\Scripts\python.exe`.

Why:
- Notebook code runs in the same environment as scripts.

### Step 8) Verify everything works

In a notebook cell, run:

```python
import sys
print(sys.executable)
import numpy, pandas
print("Environment OK")
```

What you should see:

1. A path like `<venv-path>\Scripts\python.exe`.
2. The line `Environment OK`.

### Step 9) Test your script

From terminal (with environment active), run:

```powershell
python scripts/run_phase2_notebook.py --preflight-only
python scripts/run_phase2_notebook.py
```

---

## What to do with the old `.venv` in project folder

Only after both computers are working with a machine-local environment such as `<venv-path>`:

1. Delete the old project `.venv` folder.
2. Keep using only machine-local environments.

---

## VS Code settings recommendation

If `.vscode/settings.json` currently forces `${workspaceFolder}\\.venv\\Scripts\\python.exe`, remove that setting.

Why:
- It points VS Code to the old synced environment.
- You now want VS Code to use the machine-local interpreter.

---

## If a command fails

### If `python` is not recognized

Install Python from python.org, then restart VS Code.

### If activation is blocked by PowerShell policy

Run this in terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### If packages still fail to import

Check interpreter path:

```powershell
python -c "import sys; print(sys.executable)"
```

It must point to `C:\venvs\sensor_project\Scripts\python.exe`.
It must point to `<venv-path>\Scripts\python.exe`.

---

## Daily workflow

Each time you start work:

1. Open terminal in project folder.
2. Activate environment:

```powershell
<venv-path>\Scripts\Activate.ps1
```

If you prefer to keep the environment inside the repository for a single-computer workflow, use `.venv` and keep that folder ignored in Git.

3. Run scripts or notebooks.

---

## Why this solves the sync problem

1. Project code remains synced across computers.
2. Python environment stays local and stable on each machine.
3. No cross-machine path mismatch inside virtual environment files.

You get reproducible behavior without sharing a fragile `.venv` folder.
