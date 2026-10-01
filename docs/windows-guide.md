# Windows guide for beginners

This guide assumes you have never used a terminal. You will copy and paste a few lines, once. After that, converting a file is a double-click.

You need about 10 minutes and an internet connection for the setup. Converting files afterwards works offline.

## Part 1: Install Python (once)

md2textbook is written in Python, a free program that needs to be installed first.

1. Open your web browser and go to **https://www.python.org/downloads/**
2. Click the big yellow button **Download Python 3.x.x**. Any version from 3.10 up is fine.
3. When the download finishes, open the file (for example `python-3.13.0-amd64.exe`) from your Downloads folder.
4. **Important:** at the bottom of the first window, tick the box **Add python.exe to PATH**. If you skip this, the next part will not work.
5. Click **Install Now**, and click **Yes** if Windows asks for permission.
6. Wait until it says "Setup was successful", then click **Close**.

## Part 2: Install md2textbook (once)

1. Click the Windows **Start** button (or press the Windows key).
2. Type `PowerShell`. A blue "Windows PowerShell" app appears.
3. Click it. A window with white text on a dark background opens. This is the terminal. You only need to type two things into it.
4. Click in the window, then copy the line below and paste it with a **right-click** (right-clicking pastes in this window). Press **Enter**.

   ```
   python -m pip install md2textbook
   ```

5. Wait. Lots of text scrolls by for a minute or two. It is finished when you see a new line ending with `>` and the last messages say `Successfully installed md2textbook-...`.
6. Check that it worked. Paste this and press **Enter**:

   ```
   python -m md2textbook --version
   ```

   It should print `md2textbook 0.1.x`. You can close the window now.

## Part 3: Make a desktop shortcut (once)

This gives you an icon to double-click, so you never need the terminal again.

1. Right-click an empty spot on your **Desktop**.
2. Choose **New → Shortcut**.
3. Where it asks for the location of the item, type exactly:

   ```
   pyw -m md2textbook
   ```

4. Click **Next**.
5. Name it `Markdown to PDF`, then click **Finish**.

If Windows says it cannot find the item in step 3, open PowerShell, run `where pyw`, and use the path it prints followed by ` -m md2textbook` (for example `C:\Users\YourName\AppData\Local\Programs\Python\Launcher\pyw.exe -m md2textbook`).

## Part 4: Convert a file

**Option A: choose the file**
1. Double-click the **Markdown to PDF** icon.
2. A window opens asking you to select a file. Find your `.md` file and click **Open**.
3. After a few seconds the PDF appears, and it is saved next to your `.md` file with the same name.

**Option B: drag and drop**
1. Drag your `.md` file and drop it onto the **Markdown to PDF** icon on the Desktop.
2. The PDF is created next to your file and opens by itself.

If the images in your Markdown file do not show up, keep the image files in the same folder as the `.md` file, or in the folder the file refers to.

## Updating later

Open PowerShell as in Part 2 and paste:

```
python -m pip install --upgrade md2textbook
```

## If something goes wrong

| What you see | What to do |
|---|---|
| `'python' is not recognized as an internal or external command` | Python was installed without the PATH box ticked. Run the Python installer again, choose **Modify**, then **Next**, tick **Add Python to environment variables**, and click **Install**. Then close and reopen PowerShell. |
| The Microsoft Store opens when you type `python` | Python is not installed yet, or the PATH box was not ticked. Repeat Part 1, then reopen PowerShell. |
| Double-clicking the icon does nothing | Open PowerShell and run `python -m md2textbook`. If you see an error, send it to us in an issue. |
| A box says "Conversion failed" | Your file may use something unsupported. Send the message (and, if you can, the file) in an issue. |
| Part of an equation shows as plain text | md2textbook supports most LaTeX, but not matrices or custom macros. See "Limitations" in the README. |
| The PDF is saved as `name (2).pdf` | The old PDF was still open in a viewer. Close it and convert again. |

Report problems at https://github.com/MikeDegany/md2textbook/issues/new/choose and include the exact message you saw.
