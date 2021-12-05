# lumbermixalot
Blender 2.80 (Works with 2.93.1) Add-On to make Mixamo assets (Characters and Animations) compatible with O3DE game engine

CAVEAT: 
1. Not tested with older versions of Blender.

# YouTube Tutorial
https://youtube.com/playlist?list=PL80dW98K-QMe5jvzvXlln0utWgJ9sCIfR

# How To Use
## Long Story Short
#### 2. Install Lumbermixalot as a Blender AddOn
- Download the script as a ZIP file.
- Open Blender. Menu option Edit --> Preferences
- Click *Add-ons* button.
- Click *Install an add-on* button.
- select the ZIP file.
The Lumbermixalot plugin is located inside the "3D Viewport" as a Panel in the Properties region (Press N Key). You should see a tab named *Lumbermixalot* next to *View*, *Tool* and *Item* tabs.

## Running Lumbermixalot as a regular python script (For Developers)
If you want to modify or debug Lumbermixalot, then don't install it.
Simply clone this repository or extract the content of the ZIP file.
Let's assume you checkout/download the code at:
*C:\\path\\to\\lumbermixalot*

Paste the following code in the Blender Text View.
```python
import bpy
import os
import sys

projdir = "E:\\GIT\\lumbermixalot"
if not projdir in sys.path:
    sys.path.append(projdir)

filename = os.path.join(projdir, "__init__.py")
exec(compile(open(filename).read(), filename, 'exec'))
```
Click the *Run Script* button. The Lumbermixalot UI will appear inside the "3D Viewport" as a Panel in the Properties region (Press N Key). You should see a tab named *Lumbermixalot* next to *View*, *Tool* and *Item* tabs.

Quick Tip to clear the 'System Console'
```python
import os
os.system('cls')
```
