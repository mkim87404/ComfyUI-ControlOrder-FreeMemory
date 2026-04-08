import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "comfyui.adaptive.infinite.io",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "ControlOrderFreeMemory") return;

        // Keep original trigger logic
        const originalOnConnectionsChange = nodeType.prototype.onConnectionsChange;

        nodeType.prototype.onConnectionsChange = function (type, index, isConnected, linkInfo) {
            // Execute original trigger logic & keep its return value
            const originalReturnValue = originalOnConnectionsChange?.apply(this, arguments);

            // New extended logic - Dynamically increase Input & Output slots on the "ControlOrderFreeMemory" node
            if (type === 1 && isConnected && linkInfo != null && this.inputs[index].name.startsWith("persist_any_") && (this.inputs.length === 2 || index === this.inputs.length - 1)) {
                // Only trigger on input connections (type === 1 && isConnected)
                // Do not trigger when the node is being copied over (linkInfo != null)
                // Only trigger slot expansion when the last input slot is connected (index === this.inputs.length - 1).

                // Define & Add new Input & Output slots
                const newSlotName = `persist_any_${this.inputs.length}`
                const newSlotType = this.inputs[index].type || "*";

                // All connected input slots will correctly send their data to **kwargs in Python backend
                this.addInput(newSlotName, newSlotType);    // Currently, there is no supported way to set a tooltip on dynamically created slots.
                this.addOutput(newSlotName, newSlotType);

                // Force UI refresh
                this.setDirtyCanvas(true, true);
            }
            // To-Do/Good-To-Have: Remove slots on disconnect? - Functionally redundant for now

            // Return the original function return value, to not break anything.
            return originalReturnValue;
        };
    },
});