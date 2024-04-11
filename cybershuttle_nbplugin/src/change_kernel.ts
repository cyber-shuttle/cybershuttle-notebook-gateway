// // src/index.ts
// import { JupyterFrontEnd, JupyterFrontEndPlugin } from '@jupyterlab/application';
// import { showDialog, Dialog, IClientSession } from '@jupyterlab/apputils';

// const PLUGIN_ID = 'my-extension:change-kernel';

// const extension: JupyterFrontEndPlugin<void> = {
//   id: PLUGIN_ID,
//   autoStart: true,
//   activate: async (app: JupyterFrontEnd) => {
//     app.commands.addCommand(PLUGIN_ID, {
//       label: 'Change Kernel',
//       execute: async () => {
//         // Implement your custom logic here
//         // For example, you can show a dialog to choose a kernel
//         const sessions = app.serviceManager.sessions;
//         const specs = await app.serviceManager.kernelspecs.listSpecs();
        
//         // Logic to choose kernel...
//         // For demonstration, let's just show a dialog with kernel names
//         const kernelNames = Object.keys(specs.kernelspecs);
//         const result = await showDialog({
//           title: 'Select Kernel',
//           body: new Dialog.Body({ items: kernelNames }),
//           buttons: [Dialog.cancelButton(), Dialog.okButton({ label: 'Change' })]
//         });

//         if (result.button.accept && result.value) {
//           // Get the selected kernel name
//           const selectedKernelName = result.value as string;

//           // Change kernel
//           const session = await sessions.findByPath(app.shell.currentWidget?.context.path);
//           if (session) {
//             await session.changeKernel({ name: selectedKernelName });
//           }
//         }
//       }
//     });

//     // Override default "Change Kernel" command
//     app.commands.oe.overrideBuiltins({
//       'kernel:change-kernel': {
//         ...app.commands.builtins['kernel:change-kernel'],
//         execute: () => app.commands.execute(PLUGIN_ID)
//       }
//     });
//   }
// };

// export default extension;
