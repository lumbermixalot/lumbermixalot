# lumbermixalot
Blender 2.80 Add-On to make Mixamo Rigs (Characters and Animations) compatible with O3DE game engine

CAVEAT: 
1. Not tested with older versions of Blender.

# YouTube Tutorial
(For v1.1.1 compatible with Lumberyard 1.2X. Do not follow the tutorial if using O3DE)
https://www.youtube.com/playlist?list=PL80dW98K-QMcC-i0OHk0ZjSCS88wscRHc

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

projdir = "C:\\path\\to\\lumbermixalot"
if not projdir in sys.path:
    sys.path.append(projdir)

filename = os.path.join(projdir, "__init__.py")
exec(compile(open(filename).read(), filename, 'exec'))
```
Click the *Run Script* button. The Lumbermixalot UI will appear inside the "3D Viewport" as a Panel in the Properties region (Press N Key). You should see a tab named *Lumbermixalot* next to *View*, *Tool* and *Item* tabs.
