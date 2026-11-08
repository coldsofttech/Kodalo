import { useEffect, useState } from 'react';
import { listAiConnections, listAiTaskModels, setAiTaskModel } from '../../../libs/api.js';
import { Button, Select } from '../../../components/controls.jsx';
import { useUnsavedGuard } from '../../../libs/unsaved.js';

/** @typedef {{ task: string, label: string, description: string, model: string | null }} AiTaskModel */

/** The model each job done by AI uses, chosen from the models of the default connection. */
export default function AiTaskModels() {
  const [tasks, setTasks] = useState(/** @type {AiTaskModel[] | null} */ (null));
  const [models, setModels] = useState(/** @type {string[]} */ ([]));
  const [fallback, setFallback] = useState('');
  const [choices, setChoices] = useState(/** @type {Record<string, string>} */ ({}));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(
    /** @type {{ ok: boolean, text: string } | null} */ (null),
  );

  /** @param {AiTaskModel[]} list @param {string[]} offered */
  const remember = (list, offered) =>
    setChoices(
      Object.fromEntries(
        list.map((item) => [
          item.task,
          item.model && offered.includes(item.model) ? item.model : '',
        ]),
      ),
    );

  useEffect(() => {
    let alive = true;
    Promise.all([listAiConnections(), listAiTaskModels()]).then(
      ([connections, list]) => {
        if (!alive) return;
        const active = connections.find(
          (/** @type {{ is_default: boolean, enabled: boolean }} */ c) => c.is_default && c.enabled,
        );
        const offered = (active?.models ?? []).map((/** @type {{ name: string }} */ m) => m.name);
        setModels(offered);
        setFallback(active?.default_model ?? '');
        setTasks(list);
        remember(list, offered);
      },
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, []);

  const changed = (tasks ?? []).some((item) => (item.model ?? '') !== (choices[item.task] ?? ''));
  useUnsavedGuard(changed);

  async function save() {
    setBusy(true);
    setMessage(null);
    try {
      let latest = tasks ?? [];
      for (const item of tasks ?? []) {
        const wanted = choices[item.task] ?? '';
        if ((item.model ?? '') !== wanted) {
          latest = await setAiTaskModel(item.task, wanted || null);
        }
      }
      setTasks(latest);
      remember(latest, models);
      setMessage({ ok: true, text: 'Saved.' });
    } catch (failure) {
      setMessage({
        ok: false,
        text: failure instanceof Error ? failure.message : 'Something went wrong.',
      });
    } finally {
      setBusy(false);
    }
  }

  if (error) {
    return (
      <p role="alert" className="alert">
        {error}
      </p>
    );
  }
  if (!tasks) return <p>Loading…</p>;
  if (models.length === 0) {
    return (
      <p className="hint">
        Save an AI connection and add its models above, then choose which model each job uses.
      </p>
    );
  }
  return (
    <div className="ai-task-models">
      <p className="hint">
        Each job uses the model you choose from the active connection. Jobs left on the default use{' '}
        {fallback ? <strong>{fallback}</strong> : 'the default model'}.
      </p>
      {tasks.map((item) => (
        <Select
          key={item.task}
          label={item.label}
          value={choices[item.task] ?? ''}
          onChange={(value) => setChoices((current) => ({ ...current, [item.task]: value }))}
        >
          <option value="">Use the default{fallback ? ` (${fallback})` : ''}</option>
          {models.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </Select>
      ))}
      {message ? (
        <p role={message.ok ? 'status' : 'alert'} className={message.ok ? 'notice' : 'alert'}>
          {message.text}
        </p>
      ) : null}
      <div className="row actions">
        <Button
          appearance="accent"
          disabled={busy || !changed}
          onClick={save}
          label="Save models"
          title="Save models"
        >
          <i className="bi bi-floppy" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
