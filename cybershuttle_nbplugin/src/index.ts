import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { DocumentRegistry, IDocumentWidget } from '@jupyterlab/docregistry';
import { ILauncher } from '@jupyterlab/launcher';
import { INotebookModel, NotebookPanel } from '@jupyterlab/notebook';
import { ISettingRegistry } from '@jupyterlab/settingregistry';

import { ToolbarButton } from '@jupyterlab/ui-components';

import { Dialog } from '@jupyterlab/apputils';
import { IDisposable } from '@lumino/disposable';
import { CybershuttleKernelLauncher } from './kernel_launcher';

/**
 * Initialization data for the cybershuttle_nbplugin extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: `cybershuttle_nbplugin:plugin`,
  description: 'Notebook Extension for Running Remote Kernels via Cybershuttle',
  autoStart: true,
  optional: [ISettingRegistry, ILauncher],
  activate: activate_cybershuttle_launcher
};

async function activate_cybershuttle_launcher(
  app: JupyterFrontEnd,
  settingRegistry: ISettingRegistry,
  launcher: ILauncher
) {
  console.log('JupyterLab extension cybershuttle_nbplugin is activated!');

  if (settingRegistry) {
    try {
      const settings = await settingRegistry.load(plugin.id);
      console.log('cybershuttle_nbplugin settings loaded:', settings.composite);
    } catch (reason) {
      console.error('error loading cybershuttle_nbplugin settings:', reason);
    }
  }

  const CMD_CREATE = 'cybershuttle:create_kernel';
  const CMD_UPDATE = 'cybershuttle:switch_kernel';
  const CMD_CHOOSE = 'cybershuttle:pick_kernel';
  type X = DocumentRegistry.IWidgetExtension<NotebookPanel, INotebookModel>;

  class CybershuttleButton implements X {
    createNew(
      panel: NotebookPanel,
      context: DocumentRegistry.IContext<INotebookModel>
    ): IDisposable {
      // Create the toolbar button
      let cybershuttle = new ToolbarButton({
        label: 'Cybershuttle Kernel',
        onClick: () => app.commands.execute(CMD_CHOOSE, { action: CMD_UPDATE })
      });

      // Add the toolbar button to the notebook toolbar
      panel.toolbar.insertItem(10, 'cybershuttle', cybershuttle);

      // The ToolbarButton class implements `IDisposable`, so the
      // button *is* the extension for the purposes of this method.
      return cybershuttle;
    }
  }

  app.commands.addCommand(CMD_UPDATE, {
    label: 'Change to Cybershuttle Kernel',
    execute: async args => {
      try {
        // save args to kernelspec
        console.log(args);
        // reload kernelspecs
        const services = app.serviceManager;
        await services.ready;
        const specs = services.kernelspecs;
        await specs.ready;
        // get kernel info
        const kernel_name = 'gkeyll';
        // update notebook with new kernel
        const cw = app.shell.currentWidget;
        if (cw! instanceof NotebookPanel) {
          const notebookPanel = cw;
          const sessionContext = notebookPanel.sessionContext;
          await sessionContext.changeKernel({});
          return sessionContext.changeKernel({ name: kernel_name });
        }
      } catch (err) {
        console.error(err);
      }
    }
  });

  app.commands.addCommand(CMD_CREATE, {
    label: 'Create With Cybershuttle Kernel',
    execute: async args => {
      try {
        // save args to kernelspec
        console.log(args);
        // reload kernelspecs
        const services = app.serviceManager;
        await services.ready;
        const specs = services.kernelspecs;
        await specs.ready;
        // launch kernel and open notebook
        const cwd = '.';
        const kernel_name = 'gkeyll';
        // open notebook with kernel
        const widget = (await app.commands.execute('docmanager:open', {
          path: `${cwd}/example.ipynb`,
          factory: 'Notebook',
          kernel: {}
        })) as IDocumentWidget;
        widget.isUntitled = true;
        return widget.context.sessionContext.changeKernel({
          name: kernel_name
        });
      } catch (err) {
        console.error(err);
      }
    }
  });

  app.commands.addCommand(CMD_CHOOSE, {
    label: 'Select Cybershuttle Kernel',
    execute: async (args: any) => {
      try {
        const res = await fetch(
          'http://74.235.88.134/kernelspecs?user=yasith',
          {
            mode: 'cors'
          }
        );
        const json = await res.json();
        const clusters = Object.keys(json);
        const cfg = json.gkeyll.metadata.kernel_provisioner.config;
        const spec = cfg.spec;
        const workdir = String(cfg.workdir);
        // create dialog to provide kernel specs
        const dialog = new Dialog<any>({
          title: 'Select Kernel',
          body: new CybershuttleKernelLauncher(clusters, workdir, spec),
          buttons: [Dialog.cancelButton(), Dialog.okButton({ label: 'Launch' })]
        });
        // handle dialog output
        const result = await dialog.launch();
        if (result.button.accept) {
          console.log(args.action, result.value);
          await app.commands.execute(args.action, result.value);
        }
      } catch (err) {
        console.error(err);
      }
    }
  });

  launcher.add({
    command: CMD_CHOOSE,
    category: 'Cybershuttle',
    args: { action: CMD_CREATE }
  });

  app.docRegistry.addWidgetExtension('Notebook', new CybershuttleButton());
}

export default plugin;
