# lumbermixalot
Blender Add-On to make Mixamo Rigs (Characters and Animations) compatible with Amazon Lumberyard game engine
------------------------------------------------------------------------------------------------------------

# How To Use

Clone/Download the code.
Open Blender.
Open Text View.
Paste the following code:

-------------------------------------
import bpy
import os
import sys

projdir = "C:\\path\\to\\lumbermixalot"
if not projdir in sys.path:
    sys.path.append(projdir)

filename = os.path.join(projdir, "__init__.py")
exec(compile(open(filename).read(), filename, 'exec'))
-------------------------------------

Click the "Run Script" button and the "Lumbermixalot" TAB should show up next to "View", "Tool" and "Item" tabs.
