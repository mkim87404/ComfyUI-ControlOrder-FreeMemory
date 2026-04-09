import comfy.model_management as model_management
import gc
import torch
import psutil

class AnyType(str):
    def __ne__(self, __value: object) -> bool:  # Make this class instance be equal to everything, to bypass ComfyUI's type validation check.
        return False

anyType = AnyType("*")

class MatryoshkaTuple(tuple):
    def __getitem__(self, index):   # Override the tuple "__getitem__" to always return the 1st element. This allows the node's return tuple to grow dynamically while ComfyUI believes the tuple length is still 1.
        if index > 0:
            index = 0
        return super().__getitem__(index)

class ControlOrderFreeMemory:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "free_memory": ("BOOLEAN", {
                    "default": False,
                    "tooltip": "Unload all models and release as much VRAM & RAM as possible while routing & preserving all 'persist_any' passthrough data. Any models passed into 'persist_any' will stay loaded if they were not already unloaded by the sender nodes (e.g. CLIP / some GGUF loaders). Prints how much VRAM & RAM has been freed on the ComfyUI session terminal.",
                }),
            },
            "optional": {
                "persist_any_1": (anyType, {
                    "tooltip": "Persist any type of data through to the next node e.g. latents, conditioning, images, masks, models (except CLIP / some GGUF models already unloaded by the sender nodes), etc. This data survives the 'free_memory' operation. I/O slots expand adaptively",
                }),
            }
        }

    @classmethod
    def VALIDATE_INPUTS(cls, **kwargs):
        return True

    OUTPUT_NODE = True  # Let this be a hybrid node that can both be in the middle or at the end of a workflow (with no outputs connected).
    RETURN_TYPES = MatryoshkaTuple((anyType, )) # Let this node's output slot cardinality grow dynamically from JS hooks, while ComfyUI type validation check believes this is just a tuple of 1 "AnyType" element.
    RETURN_NAMES = MatryoshkaTuple(("persist_any_1", )) # Same trick
    OUTPUT_TOOLTIPS = MatryoshkaTuple(("Persist any type of data through to the next node e.g. latents, conditioning, images, masks, models (except CLIP / some GGUF models already unloaded by the sender nodes), etc. This data survives the 'free_memory' operation. I/O slots expand adaptively", ))
    FUNCTION = "passthrough"
    CATEGORY = "Control Order & Free Memory"
    DESCRIPTION = """Control the execution order of nodes by routing any data (as many as you need - I/O slots expand adaptively) through this node. Ensures all input-connected nodes finish executing first before the output-connected nodes start executing.

All input & output slots are AnyType (*). They can hook onto any node, including loader-type nodes like "Load Model", "Load VAE", "Load CLIP", etc. For connecting into loader-type nodes, you can use the "📁 Filename Selector" helper node (already installed with this custom node) to select & feed the filename into the input "persist_any_N" slot that corresponds to the output "persist_any_N" slot that is connecting into the loader-type node.

Optionally unload all models and release as much VRAM & RAM as possible while routing & preserving all 'persist_any' passthrough data. Any models passed into 'persist_any' will stay loaded if they were not already unloaded by the sender nodes (e.g. Load CLIP / some GGUF loaders, etc.) This node will also print how much VRAM & RAM has been freed on the ComfyUI session terminal.
"""

    def passthrough(self, **kwargs):
        # Collect every connected input (only connected slots appear in kwargs when the prompt is sent)
        input_keys = [key for key in kwargs if key.startswith("persist_any_")]
        
        # Secure the input values in the exact order they were connected - to persist them throughout the potential memory cleanup operation
        if input_keys:
            #  Sort the connected inputs in the exact order they were added
            input_keys.sort(key=lambda input_key: int(input_key[12:]))
            output_values = [None] * int(input_keys[-1][12:])  # Only need to define output up to the highest seen persist_any_N, and let ComfyUI output None for any undefined outputs beyond N.
            for input_key in input_keys:
                output_values[int(input_key[12:]) - 1] = kwargs[input_key]
        else:
            output_values = [None]

        # Run only if "free_memory" was toggled ON
        if kwargs.get("free_memory"):
            print("🔷 Control Order & Free Memory • Full VRAM & RAM cleanup 🔷")

            try:
                # Take snapshot of VRAM before cleanup
                if torch.cuda.is_available():                              # NVIDIA
                    initial_vram = torch.cuda.memory_allocated()
                elif hasattr(torch, 'mps') and torch.mps.is_available():   # Apple Silicon
                    initial_vram = torch.mps.current_allocated_memory()
                elif hasattr(torch, 'xpu') and torch.xpu.is_available():   # Intel XPU
                    initial_vram = torch.xpu.memory.memory_allocated()
                elif hasattr(torch, 'npu') and torch.npu.is_available():   # Ascend NPU
                    initial_vram = torch.npu.memory_allocated()
                elif hasattr(torch, 'mlu') and torch.mlu.is_available():   # Cambricon MLU
                    initial_vram = torch.mlu.memory_allocated()
                else:                                                      # CPU / fallback
                    initial_vram = None

                # Take snapshot of RAM before cleanup
                initial_ram = psutil.virtual_memory().used   # This is fully cross-platform & included in all ComfyUI installations.

                # If any of the inputs were models (and were not already unloaded by the sender nodes, e.g. CLIP / some GGUF loaders), keep them loaded
                loaded_models = model_management.loaded_models()    # returns a list of the actual model objects currently tracked by ComfyUI in current_loaded_models
                keep_loaded = []
                for key in input_keys:
                    if kwargs[key] in loaded_models:  # if any of the inputs was a model that's currently loaded, keep it loaded.  
                        keep_loaded.append(kwargs[key])

                # Unload everything else
                if keep_loaded:
                    model_management.free_memory(1e30, model_management.get_torch_device(), keep_loaded)
                    # This is the core "free as much VRAM as possible" function, where "1e30" means "free this large amount of memory (i.e. everything)". It walks the ComfyUI internal list "current_loaded_models", skips unloading anything in keep_loaded, calls model_unload() on the rest (which does the model unload/detach, unpatch weights, set real_model=None, and for some models a controlled partially_unload() to the offload device - no forced CPU offload unless the model itself decides to partially unload), pops them from current_loaded_models, then calls cleanup_models_gc() (which conditionally runs gc.collect() + soft_empty_cache() if any momdel in current_loaded_models is_dead() i.e. memory leak is suspected) and soft_empty_cache() once (if it unloaded at least 1 model).
                    # This is the official ComfyUI maintained method that safely manages its internal model load states through current_loaded_models entries and other internal memory accounting.
                    print("  - All models unloaded (except models connected into persist_any)")
                else:
                    model_management.unload_all_models()
                    # This just calls free_memory(1e30, get_torch_device()) with no keep_loaded models list, defaulting it to [] (i.e. it unloads all models).
                    # This is the official ComfyUI maintained method that safely manages its internal model load states through current_loaded_models entries and other internal memory accounting.
                    print("  - All models unloaded")

                print("  - Synchronizing hardware accelerator")
                model_management.soft_empty_cache(True)
                # This is a device-agnostic wrapper that does:
                # → CUDA: torch.cuda.synchronize() + torch.cuda.empty_cache() + torch.cuda.ipc_collect()
                # → MPS / XPU / NPU / MLU: runs the equivalent empty_cache for that backend, and the force param is ignored in current ComfyUI (legacy).
            except Exception as e:
                print(f"  - Non-fatal error during unload: {e}")
            finally:
                # First pass (Device-agnostic empty_cache)
                # DESIGN: While model_management.soft_empty_cache(True) is a convenient one-liner for cross-device empty_cache(), I've extracted all the cross-device operations to extend & optimize the cleanup sequence per device, while skipping any extra calls to torch.cuda.synchronize() which is now redundant after model_management.soft_empty_cache(True)
                print("  - Clearing VRAM")
                if torch.cuda.is_available():   # NVIDIA
                    torch.cuda.empty_cache()    # releases the cached VRAM and available memory held by the allocator but not currently in use
                elif hasattr(torch, 'mps') and torch.mps.is_available():    # Apple Silicon
                    torch.mps.empty_cache()
                elif hasattr(torch, 'xpu') and torch.xpu.is_available():    # Intel XPU
                    torch.xpu.empty_cache()
                elif hasattr(torch, 'npu') and torch.npu.is_available():    # Ascend NPU
                    torch.npu.empty_cache()
                elif hasattr(torch, 'mlu') and torch.mlu.is_available():    # Cambricon MLU
                    torch.mlu.empty_cache()
                else:                                                       # CPU / fallback
                    print("    - No GPU accelerator detected.")

                print("  - Clearing RAM")
                gc.collect()    # release objects from memory that no longer have active references. Critical for freeing CPU RAM + any Python object references after the tensors are gone.

                # Second pass (catches anything GC just released + IPC on CUDA)
                if torch.cuda.is_available():                               # NVIDIA
                    torch.cuda.empty_cache()    # double empty_cache to catch lingering tensors after GC
                    torch.cuda.ipc_collect()    # frees any lingering CUDA IPC / shared-memory handles that empty_cache() sometimes misses. Useful when models were loaded with certain GGUF/quantized loaders or in multi-process scenarios. Harmless in a normal single-process ComfyUI server.
                    model_management.cleanup_models()   # lightweight & harmless "remove dead/stale model wrappers" helper that scans current_loaded_models and removes entries where real_model() is None (i.e. dead wrappers that free_memory may have left behind in some edge cases), pops them from current_loaded_models, and deletes the wrapper. This is only meaningful after the model tensors have already been unloaded + garbage-collected such that every dead model wrapper whose real_model() just became None can be caught.
                    print("  - Clearing CUDA stats")
                    try:
                        torch.cuda.reset_peak_memory_stats()    # Optional stats reset. try catch because this can raise in edge cases (no active CUDA context, older PyTorch, or after certain errors)
                    except:
                        pass
                    final_vram = torch.cuda.memory_allocated()  # Take snapshot of VRAM after cleanup
                elif hasattr(torch, 'mps') and torch.mps.is_available():    # Apple Silicon
                    torch.mps.empty_cache()
                    model_management.cleanup_models()
                    final_vram = torch.mps.current_allocated_memory()   # Take snapshot of VRAM after cleanup
                elif hasattr(torch, 'xpu') and torch.xpu.is_available():    # Intel XPU
                    torch.xpu.empty_cache()
                    model_management.cleanup_models()
                    final_vram = torch.xpu.memory.memory_allocated()    # Take snapshot of VRAM after cleanup
                elif hasattr(torch, 'npu') and torch.npu.is_available():    # Ascend NPU
                    torch.npu.empty_cache()
                    model_management.cleanup_models()
                    final_vram = torch.npu.memory_allocated()   # Take snapshot of VRAM after cleanup
                elif hasattr(torch, 'mlu') and torch.mlu.is_available():    # Cambricon MLU
                    torch.mlu.empty_cache()
                    model_management.cleanup_models()
                    final_vram = torch.mlu.memory_allocated()   # Take snapshot of VRAM after cleanup
                else:                                                       # CPU / fallback
                    final_vram = None
                
                # Take snapshot of RAM after cleanup
                final_ram = psutil.virtual_memory().used

                # Print memory analytics
                print("  - VRAM & RAM cleanup complete")
                if initial_vram is None:
                    print("    - GPU VRAM: No GPU accelerator detected.")
                else:
                    print(f"    - GPU VRAM: Initial usage: {initial_vram/1073741824:.2f} GB, Final usage: {final_vram/1073741824:.2f} GB, Freed: {(initial_vram - final_vram)/1073741824:.2f} GB")   # 1073741824 == (1024 ** 3)
                print(f"    - System RAM: Initial usage: {initial_ram/1073741824:.2f} GB, Final usage: {final_ram/1073741824:.2f} GB, Freed: {(initial_ram - final_ram)/1073741824:.2f} GB")

        return tuple(output_values)

class FileNameSelector:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "string": ("STRING", {
                    "default": "",
                    "multiline": False,
                    "tooltip": "Select a filename and further edit the string here."
                }),
            }
        }

    OUTPUT_NODE = True
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("STRING",)
    OUTPUT_TOOLTIPS = ("Final string for downstream use", )
    FUNCTION = "select_filename"
    CATEGORY = "Control Order & Free Memory"
    DESCRIPTION = "Select a filename from your native OS file picker and optionally edit the string for downstream use."

    def select_filename(self, string):
        return (string,)