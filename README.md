# lumbermixalot
Blender 2.80 Add-On to make Mixamo Rigs (Characters and Animations) compatible with Amazon Lumberyard game engine

# How To Use
## Long Story Short
#### 1. Modify and Recompile Lumberyard.
As of Lumberyard 1.21, parent nodes above the first root bone corrupt root motion extraction. 
Modify the file at **<LumberyardRoot>\dev\Gems\EMotionFX\Code\EMotionFX\Pipeline\RCExt\Actor\ActorBuilder.cpp** as follows: 
The code you must add is found in the section marked:
```
//LUMBERMIXALOT: Required To Support Blender Armatures START
code
//LUMBERMIXALOT: Required To Support Blender Armatures END
```
```cpp  
        void ActorBuilder::BuildPreExportStructure(ActorBuilderContext\& context,
            const SceneContainers::SceneGraph::NodeIndex\& rootBoneNodeIndex,
            const NodeIndexSet\& selectedBaseMeshNodeIndices,
            AZStd::vector<SceneContainers::SceneGraph::NodeIndex>\& outNodeIndices,
            BoneNameEmfxIndexMap\& outBoneNameEmfxIndexMap)
        {
            const SceneContainers::SceneGraph& graph = context.m_scene.GetGraph();
            const Group::IActorGroup& group = context.m_group;

            auto nameStorage = graph.GetNameStorage();
            auto contentStorage = graph.GetContentStorage();
            auto nameContentView = SceneViews::MakePairView(nameStorage, contentStorage);

            // The search begin from the rootBoneNodeIndex.
            auto graphDownwardsRootBoneView = SceneViews::MakeSceneGraphDownwardsView<SceneViews::BreadthFirst>(graph, rootBoneNodeIndex, nameContentView.begin(), true);
            auto it = graphDownwardsRootBoneView.begin();
            if (!it->second)
            {
                // We always skip the first node because it's introduced by scenegraph
                ++it;
                if (!it->second && it != graphDownwardsRootBoneView.end())
                {
                    // In maya / max, we skip 1 root node when it have no content (emotionfx always does this)
                    // However, fbx doesn't restrain itself from having multiple root nodes. We might want to revisit here if it ever become a problem.
                    ++it;
                }
            }

            //LUMBERMIXALOT: Required To Support Blender Armatures START
            //If the root node is not a root bone, skip it.
            auto bone = azrtti_cast<const SceneDataTypes::IBoneData*>(it->second);
            if (!bone)
            {
                AZ_TracePrintf(SceneUtil::WarningWindow, "Skipping root node because it is not a root bone.\n");
                ++it;
            }
            //LUMBERMIXALOT: Required To Support Blender Armatures END
            
            //The rest of the code remains the same.
            ...
            ...
        }
```
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
