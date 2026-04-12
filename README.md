# ComfyUI-ControlOrder-FreeMemory

[![ComfyUI](https://img.shields.io/badge/ComfyUI-Node-blue)](https://github.com/comfyanonymous/ComfyUI)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.x-orange)](https://pytorch.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![ComfyUI Node Screenshot](https://github.com/user-attachments/assets/792c727e-ad57-488f-b827-7e5ceccee32e)](https://github.com/user-attachments/assets/792c727e-ad57-488f-b827-7e5ceccee32e)

`🔷 Control Order & Free Memory` is a dependency-free ComfyUI custom node for controlling the execution order of nodes by routing any type/number of data through it, ensuring all input connections resolve first before being passed to outputs. Optionally free VRAM & RAM at any point in a workflow using device-agnostic & robust memory management utilities managed by ComfyUI that safely unload all models (except any live models passing though this node) and release as much VRAM & RAM as possible, while preserving all connected passthrough data (e.g. latents, conditioning, images, masks, models, etc.) through to the next node. This node will also print a descriptive message on the ComfyUI session terminal showing how much VRAM & RAM has been freed.

All input & output slots are AnyType (*). They can hook onto any node, including loader nodes like "Load Model", "Load VAE", "Load CLIP", etc. that usually don't have any connectable input slots, making linear connection/chaining of all node types possible - enforcing a single, sequential & deterministic flow of execution. This node adaptively expands its input & output slots to support infinitely many passthrough data (persist_any_N), passing every input to their corresponding "N"th output slot unchanged.

The memory clean up + linear passthrough of data facilitated by this node can help to **speed up workflows** involving multiple models (e.g. CLIP, VAE, Diffusion Model, etc.) that compete for the same VRAM/RAM but don't all need to be loaded at the same time, by separating each model's operation into its own segment and linearly chaining them together with multiple instances of this node, where only the necessary outputs of each segment (e.g. latents, conditioning, images, models, etc.) are passed on to the next segment while unloading all/some models that are no longer needed in the workflow.

This becomes especially effective in freeing VRAM/RAM between multiple KSamplers (e.g. Wan 2.2 High & Low KSamplers), or before & after VAE Encode / VAE Decode / Load CLIP / Load Model / etc. that allow more of the models' layers to be loaded onto the GPU VRAM and less offloaded to the slower System RAM, resulting in faster overall inference times and letting the user push to higher resolution media outputs before hitting OOM. I have personally seen great reductions in total execution time of my workflows using this node.

## 🛠️ Installation

1. Clone the repo into your `ComfyUI/custom_nodes` folder:

   ```bash
   git clone https://github.com/mkim87404/ComfyUI-ControlOrder-FreeMemory.git
   ```
2. Restart the ComfyUI server, double click anywhere in the workflow and search for "**Control Order & Free Memory**" or alternatively, [Right click > Add Node > Control Order & Free Memory]

## 🔄 Update

1. To get the latest updates, run `git pull` inside the node's folder:

    ```bash
    cd custom_nodes/ComfyUI-ControlOrder-FreeMemory
    git pull
    ```

## 🎨 Example Workflow

In the `example_workflows/` folder of this repo, I have included example Wan 2.2 and LTX 2.3 T2V & I2V ComfyUI workflows using this node. Simply drag and drop the .json files into the ComfyUI browser tab to start using them. These workflows demonstrate how this node can be used to achieve a single sequential flow of execution, loading & unloading only the necessary model at each section of the workflow before progressing to the next.

## 🚀 Usage & Tips

- **Control execution order & free memory:**

    The `🔷 Control Order & Free Memory` node ensures that all of the input-connected nodes finish executing first before the output-connected nodes start executing. Hence to control the execution order of nodes, you can split your workflow into multiple groups of nodes with differing execution priorities and connect all nodes that should execute first to the input slots of this node, and all nodes that should execute later to the output slots of this node, ensuring that the correct data is being passed from the "persist_any_N" input slot to its corresponding "N"th output slot. You can then chain additional groups of nodes with as many `🔷 Control Order & Free Memory` nodes as you need, until all groups of nodes are connected together to form a single, sequential flow of execution from start to finish. Optionally, toggle "free_memory" ON on this node to unload all models and free as much VRAM & RAM as possible at the node's position, while preserving all the passthrough data. You can connect as many passthrough data as you need through this node, and each of them can be a different data type (e.g. latents, conditioning, images, models, etc.). If any of the passthrough data are models and they were not already unloaded by the sender nodes, they will stay loaded and survive the "free_memory" operation (please refer to [Limitations](#limitations) for more details). Also, when "free_memory" is ON, this node will print a descriptive message on the ComfyUI session terminal where you can check how much VRAM & RAM has been freed.

- **Connecting this node into loader-type nodes:**

    Because all input & output slots are AnyType (*), they can hook onto any node, including loader nodes like "Load Model", "Load VAE", "Load CLIP", etc. And when hooking the output of this node into those loader-type nodes, you will often notice that the only argument slot available for connection are "filename" combo/dropdown fields (STRING) for selecting the model to load. To ensure that we feed the correct value into this field, I have included a simple helper node called `📁 Filename Selector` (already included in this repo), which you can search & drop into the workflow and simply select a filaname from your native OS file explorer, and use/edit that filename string to feed it into the input slot of the `🔷 Control Order & Free Memory` node that corresponds to the output slot that is connected to the loader node's "filename" field.

- **Using this node at the start of the workflow:**

    This node can be placed anywhere in the workflow (e.g. at the very start, in the middle, at the very end, etc.), as all input & output connections are optional. And if you want this node to be at the start of the workflow e.g. to run the memory cleanup at the start of every run, you can connect ComfyUI's default `Int (Comfy Core)` node from [utils > primitive] into any input slot of `🔷 Control Order & Free Memory` node, and set the integer value to change (increment/decrement) on each run. This is to alter the input being fed into the node to trigger its memory cleanup logic at the start of each run, because ComfyUI is deigned to skip executing nodes whose inputs didn't change (which is not an issue when this node is used in the middle or at the end of a workflow). And to re-run the workflow and resume executing from the final state & outputs of the previous run, simply restore the integer value of the `Int (Comfy Core)` node back to the previous run's value, and this will ensure that running the workflow again picks up from the latest run's outputs without discarding them or incurring a re-execution of all the nodes from scratch.

- **For any uncertainties**, please refer to my included example workflow to see a working example of these nodes.

## 🍃 Features Summary

- Controls the execution order of nodes in any ComfyUI workflow to enforce a single, deterministic sequence of ordered logic.
- Securely unloads models and frees VRAM & RAM at any point in a workflow, using ComfyUI-managed & device-agnostic memory management utilities.
- All nodes are dependency-free & platform/device-agnostic.
- Adaptively expands input & output slots to support infinitely many dynamic passthrough data of any type (*).
- Linear passthrough design that focuses on one group of related nodes at a time and routes only necessary outputs to the next group of nodes helps with "cable management", tidying up the connections that can get messy as the workflow grows large, making them easier to understand and maintain.

## <a name="limitations"></a>ℹ️ Limitations

- Please note that this node is built upon the current ComfyUI implementation of the "comfy.model_management.py" module for memory management, and ComfyUI extension hooks & prototype hijacking patterns for making dynamic updates to the node's UI elements. Hence, it is possible that some features of the node may stop working in future updates of ComfyUI. For more information, you may find these Docs useful:
    - [ComfyUI model management](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy/model_management.py)
    - [ComfyUI custom extension hooks](https://docs.comfy.org/custom-nodes/js/javascript_hooks)
    - [LiteGraph.js](https://tamats.com/projects/litegraph/doc/classes/LGraphNode.html)
- You may notice that system RAM usage often does not drop as significantly as GPU VRAM does after this node's "free_memory" operation runs. This is expected behavior in the current implementation of ComfyUI, as ComfyUI intentionally caches the output of every executed node in RAM (e.g. latents, images, conditionings, tensors, etc.) with strong references that survive any py garbage collection invoked from inside the custom node's logic, and only releases those references after the entire "prompt execution" finishes (see [execution.py](https://github.com/Comfy-Org/ComfyUI/blob/master/execution.py), [comfy_execution/caching.py](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy_execution/caching.py)). This is an intentional optimization design by ComfyUI so that downstream nodes can reuse upstream outputs instantly without re-computation. The "free_memory" operation of this custom node already does the maximum possible cleanup with (model unloading + explicit gc.collect() + double device cache clearing before and after the garbage collection to collect as much lingering tensors as possible, etc.). Hence, any RAM that remains allocated after this node runs is ComfyUI's deliberate output caching, which is best to leave up to ComfyUI to manage & optimize behind the scenes across multiple workflow runs.
- CLIP models (and other text encoders) behave differently from diffusion models. In most workflows, ComfyUI automatically unloads the CLIP model immediately after the conditioning nodes (CLIPTextEncode, CLIPTextEncodeFlux, etc.) finish (see [comfy/model_management.py](https://github.com/Comfy-Org/ComfyUI/blob/master/comfy/model_management.py)). Hence, if you route the CLIP model through this node, the node will often receive an already-unloaded “husk” object, and passing this object to a later conditioning node can cause malformed conditioning outputs or OutOfMemory errors when you feed them into KSamplers. This is an inherent behaviour of the `Load CLIP (Comfy Core)` node which my custom node (that executes later in the graph) cannot prevent. As a workaround, do not rely on passing the CLIP model itself through this node. Instead, you could generate the conditioning immediately after loading CLIP, and only pass the resulting conditioning outputs through to persist_any_N. If you need the CLIP model later, you can always reload it with a new `Load CLIP (Comfy Core)` node in the subsequent chains. Diffusion models, VAEs, and most other large models managed by ComfyUI do persist correctly when routed through this node.
- Some GGUF / Quantized model loaders have custom unloading logic that may not always respect the keep_loaded feature of this node's free_memory operation, hence may drop itself before entering the node much like how CLIP models behave. But again, this can be mitigated by loading the model back in on the subsequent chains whenever you need them.
- As ComfyUI is evolving constantly, its internal model management logic can also change at any moment. So if any of the models routed through this node fail to persist or produce unexpected outcomes (e.g. CLIPTextEncode or KSamplers hang indefinitely or throw OutOfMemory errors, etc.), you can always fallback to using the models immediately after loading instead of routing them through this node, and load them back in on later chains only when they are needed again.

## ❤️ Inspired By

- [willblaschko](https://github.com/willblaschko/ComfyUI-Unload-Models) - Patterns using the "comfy.model_management" module
- [Trung0246](https://github.com/Trung0246/ComfyUI-0246) - "ByPassTypeTuple" RETURN_TYPES trick

- There were several other custom nodes solving parts of the same problem of (memory management + routing + execution order control) but I couldn't find one that combines all tricks together into a single device-agnostic node with a simple design that can take infinitely many passthrough data of any type, which encouraged me to build this custom node. I'll likely be using this node quite regularly myself, so please keep an eye out for more updates!

## 📜 License

[MIT License](https://github.com/mkim87404/ComfyUI-ControlOrder-FreeMemory/blob/main/LICENSE) – feel free to use in any personal or commercial project, fork, or open issues/PRs – contributions and feedback all welcome!