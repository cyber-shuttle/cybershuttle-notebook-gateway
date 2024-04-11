import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';
import { ILauncher } from '@jupyterlab/launcher';
import { ISettingRegistry } from '@jupyterlab/settingregistry';

import { CybershuttleKernelLauncher } from './kernel_launcher';
import { showDialog, Dialog } from '@jupyterlab/apputils';

/**
 * Initialization data for the cybershuttle_nbplugin extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'cybershuttle_nbplugin:plugin',
  description: 'Notebook Extension for Running Remote Kernels via Cybershuttle',
  autoStart: true,
  optional: [ISettingRegistry, ILauncher],
  activate: activate_cybershuttle_launcher
};

function activate_cybershuttle_launcher(
  app: JupyterFrontEnd,
  settingRegistry: ISettingRegistry,
  launcher: ILauncher
) {
  console.log('JupyterLab extension cybershuttle_nbplugin is activated!');

  if (settingRegistry) {
    settingRegistry
      .load(plugin.id)
      .then(settings => {
        console.log(
          'cybershuttle_nbplugin settings loaded:',
          settings.composite
        );
      })
      .catch(reason => {
        console.error(
          'Failed to load settings for cybershuttle_nbplugin.',
          reason
        );
      });
  }

  const CMD_LAUNCH = 'cybershuttle:launch_kernel';
  const CMD_CHOOSE = 'cybershuttle:pick_kernel';

  app.commands.addCommand(CMD_LAUNCH, {
    label: 'Launch Cybershuttle Kernel',
    execute: async specs => {
      // launch kernel and open notebook
      console.log(specs);
    }
  });

  app.commands.addCommand(CMD_CHOOSE, {
    label: 'Pick Cybershuttle Kernel',
    execute: () => {
      return fetch('http://74.235.88.134/kernelspecs?user=yasith', {
        mode: 'cors'
      })
        .then(res => res.json())
        .then(json => {
          const clusters = Object.keys(json);
          const cfg = json.gkeyll.metadata.kernel_provisioner.config;
          const spec = cfg.spec;
          const workdir = String(cfg.workdir);
          // create widget with default values returned from API
          const content = new CybershuttleKernelLauncher(
            clusters,
            workdir,
            spec
          );
          // Show widget as dialog and get response
          return showDialog<any>({
            title: 'Pick Cybershuttle Kernel',
            body: content,
            buttons: [
              Dialog.cancelButton(),
              Dialog.okButton({ label: 'Launch' })
            ]
          });
        })
        .then(result => {
          // handle dialog output
          if (result.button.accept) {
            app.commands.execute(CMD_LAUNCH, result.value);
          }
        })
        .catch(err => {
          console.error(err);
        });
    }
  });

  launcher.add({
    command: CMD_CHOOSE,
    category: 'Cybershuttle',
  });
}

export default plugin;
