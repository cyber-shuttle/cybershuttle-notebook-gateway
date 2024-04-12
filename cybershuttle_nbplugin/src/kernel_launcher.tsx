import { ReactWidget } from '@jupyterlab/apputils';

import React, { useState } from 'react';

interface KernelSpec {
  clusters: string[];
  workdir: string;
  exec_path: string;
  user_scripts: string;
  config: { [key: string]: string };
  onChange: (value: any) => void;
}

/**
 * React component for a counter.
 *
 * @returns The React component
 */
const KernelSpecForm = (props: KernelSpec) => {
  const [cluster, setCluster] = useState(props.clusters[0]);
  const [workdir, setWorkdir] = useState(props.workdir);
  const [exec_path, setExecPath] = useState(props.exec_path);
  const [user_scripts, setUserScripts] = useState(props.user_scripts);
  const [config, setConfig] = useState(props.config);

  const onChange = (key: string, value: any) => {
    let output = { cluster, workdir, exec_path, user_scripts, config }
    switch (key) {
      case 'cluster':
        output.cluster = value
        props.onChange(output)
        setCluster(_ => value);
        break;
      case 'workdir':
        output.workdir = value
        props.onChange(output)
        setWorkdir(_ => value);
        break;
      case 'exec_path':
        output.exec_path = value
        props.onChange(output)
        setExecPath(_ => value);
        break;
      case 'user_scripts':
        output.user_scripts = value
        props.onChange(output)
        setUserScripts(_ => value);
        break;
      case 'config':
        let u = { ...config, ...value }
        output.config = u
        props.onChange(output)
        setConfig(_ => u);
        break;
    }
  };
  return (
    <div>
      <div>
        <label><b>Cluster</b></label>
        <select name="cluster" value={cluster} onChange={e => onChange('cluster', e.target.value)}>
          {props.clusters.map(c => (<option value={c}>{c}</option>))}
        </select>
      </div>
      <div>
        <label><b>Working Directory</b></label>
        <input name="workdir" type="text" value={workdir} onChange={e => onChange('workdir', e.target.value)}></input>
      </div>
      <div>
        <label><b>Executable Path (Optional)</b></label>
        <input name="exec_path" type="text" value={exec_path} onChange={e => onChange('exec_path', e.target.value)}></input>
      </div>
      <div>
        <label><b>User Scripts (Optional)</b></label>
        <input name="user_scripts" type="text" value={user_scripts} onChange={e => onChange('user_scripts', e.target.value)}></input>
      </div>
      <h3 style={{ fontWeight: 'normal' }}>Choose Resources</h3>
      {Object.entries(config).map(([k, v]) => (
        <div>
          <label><b>{k}</b></label>
          <input name={k} type="text" value={v} onChange={e => onChange('config', { [k]: e.target.value })}></input>
        </div>
      ))}
    </div>
  );
};

/**
 * A Counter Lumino Widget that wraps a KernelSpecForm.
 */
class CybershuttleKernelLauncher extends ReactWidget {
  clusters: string[];
  workdir: string;
  exec_path: string;
  user_scripts: string;
  config: any;
  choice: any;
  /**
   * Constructs a new CounterWidget.
   */
  constructor(clusters: string[], workdir: string, exec_path: string, user_scripts: string, config: any) {
    super();
    this.clusters = clusters;
    this.workdir = workdir;
    this.exec_path = exec_path;
    this.user_scripts = user_scripts;
    this.config = config;
    this.choice = {
      cluster: this.clusters[0],
      workdir: this.workdir,
      exec_path: this.exec_path,
      user_scripts: this.user_scripts,
      config: config
    };
  }

  getValue() {
    return this.choice;
  }

  render(): JSX.Element {
    return (
      <KernelSpecForm clusters={this.clusters} workdir={this.workdir} exec_path={this.exec_path} user_scripts={this.user_scripts} config={this.config} onChange={value => { this.choice = value; }} />
    );
  }
}

export { CybershuttleKernelLauncher };
