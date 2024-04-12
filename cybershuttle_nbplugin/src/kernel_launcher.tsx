import { ReactWidget } from '@jupyterlab/apputils';

import React, { useState } from 'react';

interface KernelSpec {
  clusters: string[];
  workdir: string;
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
  const [config, setConfig] = useState(props.config);

  const onChange = (key: string, value: any) => {
    let output = { cluster, workdir, config }
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
  config: any;
  choice: any;
  /**
   * Constructs a new CounterWidget.
   */
  constructor(clusters: string[], workdir: string, config: any) {
    super();
    this.clusters = clusters;
    this.workdir = workdir;
    this.config = config;
    this.choice = { cluster: this.clusters[0], workdir: this.workdir, config: config };
  }

  getValue() {
    return this.choice;
  }

  render(): JSX.Element {
    return (
      <KernelSpecForm clusters={this.clusters} workdir={this.workdir} config={this.config} onChange={value => { this.choice = value; }} />
    );
  }
}

export { CybershuttleKernelLauncher };
