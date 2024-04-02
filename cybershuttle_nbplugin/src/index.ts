import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin
} from '@jupyterlab/application';

import { ISettingRegistry } from '@jupyterlab/settingregistry';

/**
 * Initialization data for the cybershuttle_nbplugin extension.
 */
const plugin: JupyterFrontEndPlugin<void> = {
  id: 'cybershuttle_nbplugin:plugin',
  description: 'Notebook Extension for Running Remote Kernels via Cybershuttle',
  autoStart: true,
  optional: [ISettingRegistry],
  activate: (app: JupyterFrontEnd, settingRegistry: ISettingRegistry | null) => {
    console.log('JupyterLab extension cybershuttle_nbplugin is activated!');

    if (settingRegistry) {
      settingRegistry
        .load(plugin.id)
        .then(settings => {
          console.log('cybershuttle_nbplugin settings loaded:', settings.composite);
        })
        .catch(reason => {
          console.error('Failed to load settings for cybershuttle_nbplugin.', reason);
        });
    }
  }
};

export default plugin;
