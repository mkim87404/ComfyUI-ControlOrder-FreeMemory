import { app } from "../../../scripts/app.js";

app.registerExtension({
    name: "comfyui.filename.selector",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name !== "FileNameSelector") return;

        const originalOnNodeCreated = nodeType.prototype.onNodeCreated;

        nodeType.prototype.onNodeCreated = function () {
            const originalReturnValue = originalOnNodeCreated?.apply(this, arguments);

            // Find the "string" input widget on the "FileNameSelector" node
            const stringInputWidget = this.widgets.find(w => w.name === "string");
            if (!stringInputWidget) return originalReturnValue;

            // Add the "Select Filename" button widget on the "FileNameSelector" node
            this.addWidget(
                "button",
                "Select Filename",
                null,
                () => {
                    // Create hidden native file input element without attaching it to DOM (i.e. the input element will be GC'd as soon as the function ends.)
                    const input = document.createElement("input");
                    input.type = "file";
                    input.style.display = "none";

                    input.onchange = (e) => {
                        const filename = e.target.files?.[0]?.name;
                        if (filename) {
                            stringInputWidget.value = filename;
                            this.setDirtyCanvas(true, true);
                        }

                        // Explicit cleanup (force immediate release & let the variables go out of scope available for GC)
                        e.target.value = "";      // reset the input so the browser drops the FileList
                        input.onchange = null;    // break any reference cycle
                    };

                    // Trigger the native OS file explorer
                    input.click();
                },
                { serialize: false }    // the "string" input widget value on the "FileNameSelector" node will not be saved into the workflow JSON
            );

            return originalReturnValue;
        };
    },
});