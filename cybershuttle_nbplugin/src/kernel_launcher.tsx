import { ReactWidget } from '@jupyterlab/apputils';

import React, { useState } from 'react';

interface KernelSpec {
  clusters: string[];
  workdir: string;
  defaults: {[key: string]: string};
  onChange: (value: any) => void;
}

/**
 * React component for a counter.
 *
 * @returns The React component
 */
const KernelSpecForm = (props: KernelSpec) => {
  const [counter, setCounter] = useState(0);
  return (
    <div>
      <p>You clicked {counter} times!</p>
      <div>
        <select name="cluster">
          {props.clusters.map(c => (
            <option value={c}>{c}</option>
          ))}
        </select>
        <input name="workdir" type="text" value={props.workdir} title="Working Directory"></input>
        {Object.entries(props.defaults).map(([k, v]) => (
          <input name={k} type="text" value={v} title={k}></input>
        ))}
      </div>
      <button
        onClick={(): void => {
          setCounter(counter + 1);
          // props.onChange(counter + 1);
        }}
      >
        Increment
      </button>
    </div>
  );
};

/**
 * A Counter Lumino Widget that wraps a KernelSpecForm.
 */
class CybershuttleKernelLauncher extends ReactWidget {
  clusters: string[];
  workdir: string;
  defaults: any;
  spec: any;
  /**
   * Constructs a new CounterWidget.
   */
  constructor(clusters: string[], workdir: string, defaults: any) {
    super();
    this.clusters = clusters;
    this.workdir = workdir;
    this.defaults = defaults;
    this.spec = { ...defaults }; // copy of defaults
  }

  getValue() {
    return this.spec;
  }

  render(): JSX.Element {
    return (
      <KernelSpecForm
        clusters={this.clusters}
        workdir={this.workdir}
        defaults={this.defaults}
        onChange={value => {}}
      />
    );
  }
}

export { CybershuttleKernelLauncher };
