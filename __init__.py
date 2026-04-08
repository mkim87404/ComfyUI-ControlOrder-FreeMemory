from .nodes import ControlOrderFreeMemory, FileNameSelector

WEB_DIRECTORY = "./js"

NODE_CLASS_MAPPINGS = {
    "ControlOrderFreeMemory": ControlOrderFreeMemory,
    "FileNameSelector": FileNameSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ControlOrderFreeMemory": "🔷 Control Order & Free Memory",
    "FileNameSelector": "📁 Filename Selector",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS", "WEB_DIRECTORY"]

__version__ = "1.0.0"