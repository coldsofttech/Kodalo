import { useEffect, useState } from 'react';
import {
  listAiConnections,
  refreshAiModels,
  removeAiConnection,
  removeAiModel,
  saveAiConnection,
  saveAiModel,
  setDefaultAiConnection,
  setDefaultAiModel,
  testAiConnection,
} from '../../api.js';
import { Button, ComboBox, Select, Switch, TextField } from '../../components/controls.jsx';

/** @typedef {{ name: string, source: string, is_default: boolean, max_tokens: number | null, temperature: number | null, timeout_s: number | null }} AiModel */
/** @typedef {{ provider: string, label: string, kind: string, saved: boolean, enabled: boolean, is_default: boolean, base_url: string, default_base_url: string, has_key: boolean, key_hint: string, status: string, status_detail: string, default_model: string | null, models: AiModel[] }} AiConnection */

const EMPTY_FORM = { name: '', maxTokens: '', temperature: '', timeout: '' };

/** @param {string} text @returns {number | null} */
const toNumber = (text) => (text.trim() === '' ? null : Number(text));

/** @param {number | null} value */
const show = (value) => (value === null ? '-' : String(value));

/** The AI providers Kodalo can connect to: one card each, with its models. */
export default function AiConnections() {
  const [connections, setConnections] = useState(/** @type {AiConnection[] | null} */ (null));
  const [error, setError] = useState('');
  const [selected, setSelected] = useState('');

  useEffect(() => {
    let alive = true;
    listAiConnections().then(
      (list) => alive && setConnections(list),
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, []);

  async function reload() {
    setConnections(await listAiConnections());
  }

  if (error) {
    return (
      <p role="alert" className="alert">
        {error}
      </p>
    );
  }
  if (!connections) return <p>Loading…</p>;
  const current = connections.find((connection) => connection.provider === selected);
  return (
    <div className="ai-connections">
      <p className="hint">
        Connect the AI services Kodalo can use. API keys are kept in the Windows credential store,
        never in Kodalo&apos;s data, and are not shown again once saved.
      </p>
      <Select label="Provider" value={selected} onChange={setSelected}>
        <option value="">Choose a provider</option>
        {connections.map((connection) => (
          <option key={connection.provider} value={connection.provider}>
            {connection.label}
          </option>
        ))}
      </Select>
      {current ? (
        <ProviderCard key={current.provider} connection={current} onReload={reload} />
      ) : null}
    </div>
  );
}

/** @param {{ connection: AiConnection, onReload: () => Promise<void> }} props */
function ProviderCard({ connection, onReload }) {
  const { provider, label } = connection;
  const needsKey = connection.kind === 'api_key';
  const [enabled, setEnabled] = useState(connection.saved && connection.enabled);
  const [key, setKey] = useState('');
  const [baseUrl, setBaseUrl] = useState(connection.base_url);
  const [form, setForm] = useState(EMPTY_FORM);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(
    /** @type {{ ok: boolean, text: string } | null} */ (null),
  );

  /** @param {() => Promise<string | void>} action */
  async function run(action) {
    setBusy(true);
    setMessage(null);
    try {
      const text = await action();
      await onReload();
      if (text) setMessage({ ok: true, text });
    } catch (failure) {
      setMessage({
        ok: false,
        text: failure instanceof Error ? failure.message : 'Something went wrong.',
      });
    } finally {
      setBusy(false);
    }
  }

  const save = () =>
    run(async () => {
      /** @type {{ enabled: boolean, api_key?: string, base_url?: string }} */
      const body = { enabled };
      if (key) body.api_key = key;
      if (needsKey) body.base_url = baseUrl;
      await saveAiConnection(provider, body);
      setKey('');
      return 'Saved.';
    });

  /** Turning a connection on or off takes effect at once, so it never waits for Save. */
  const toggle = (/** @type {boolean} */ value) => {
    setEnabled(value);
    return run(async () => {
      await saveAiConnection(provider, { enabled: value });
      return `${label} is ${value ? 'on' : 'off'}.`;
    });
  };

  const test = () =>
    run(async () => {
      const result = await testAiConnection(provider);
      if (!result.ok) throw new Error(result.detail);
      return result.detail;
    });

  const makeDefault = () =>
    run(async () => {
      await setDefaultAiConnection(provider);
      return `${label} is now the default.`;
    });

  const remove = () =>
    run(async () => {
      await removeAiConnection(provider);
      setEnabled(false);
      setKey('');
      setBaseUrl('');
      setForm(EMPTY_FORM);
      return 'Removed.';
    });

  const refresh = () =>
    run(async () => {
      const models = await refreshAiModels(provider);
      return `${models.length} models available.`;
    });

  const saveModel = () =>
    run(async () => {
      const settings = {
        max_tokens: toNumber(form.maxTokens),
        temperature: toNumber(form.temperature),
        timeout_s: toNumber(form.timeout),
      };
      for (const [field, value] of Object.entries(settings)) {
        if (Number.isNaN(value)) throw new Error(`${field.replace('_', ' ')} must be a number.`);
      }
      await saveAiModel(provider, form.name.trim(), settings);
      setForm(EMPTY_FORM);
      return 'Model saved.';
    });

  /** @param {AiModel} model */
  const editModel = (model) =>
    setForm({
      name: model.name,
      maxTokens: model.max_tokens === null ? '' : String(model.max_tokens),
      temperature: model.temperature === null ? '' : String(model.temperature),
      timeout: model.timeout_s === null ? '' : String(model.timeout_s),
    });

  /** @param {keyof typeof EMPTY_FORM} field */
  const setField = (field) => (/** @type {string} */ value) =>
    setForm((current) => ({ ...current, [field]: value }));

  /** Choosing a model that is already saved loads its settings, so it can be edited. */
  const changeName = (/** @type {string} */ value) => {
    const known = connection.models.find((model) => model.name === value);
    if (known) editModel(known);
    else setField('name')(value);
  };

  const heading = `heading-${provider}`;
  return (
    <section className="ai-card" aria-labelledby={heading}>
      <h2 id={heading}>
        {label}
        {connection.is_default ? <span className="badge">Default</span> : null}
      </h2>
      <p className="hint">
        {needsKey
          ? 'Connects with an API key.'
          : 'Uses the claude program on this computer and your own sign-in. It needs no key.'}
      </p>
      <Switch label={`${label} enabled`} checked={enabled} onChange={toggle} />
      {needsKey ? (
        <>
          <TextField
            label={`${label} key`}
            type="password"
            value={key}
            onChange={setKey}
            maxLength={512}
            hint={
              connection.has_key
                ? `A key ending in ${connection.key_hint || '…'} is saved. Enter a new one to replace it.`
                : 'No key saved yet.'
            }
          />
          <TextField
            label={`${label} address`}
            value={baseUrl}
            onChange={setBaseUrl}
            maxLength={512}
            hint={`Leave empty to use ${connection.default_base_url}.`}
          />
        </>
      ) : null}
      <div className="row actions">
        <Button appearance="accent" disabled={busy} onClick={save} label={`Save ${label}`}>
          Save
        </Button>
        <Button disabled={busy || !connection.saved} onClick={test} label={`Test ${label}`}>
          Test
        </Button>
        <Button
          disabled={busy || !connection.saved || !connection.enabled || connection.is_default}
          onClick={makeDefault}
          label={`Make ${label} the default`}
        >
          Make default
        </Button>
        <Button
          appearance="outline"
          danger
          disabled={busy || !connection.saved}
          onClick={remove}
          label={`Remove ${label}`}
        >
          Remove
        </Button>
      </div>
      {message ? (
        <p role={message.ok ? 'status' : 'alert'} className={message.ok ? 'notice' : 'alert'}>
          {message.text}
        </p>
      ) : null}
      {connection.status && !message ? (
        <p className="hint">
          Last test: {connection.status === 'ok' ? 'worked' : 'failed'}. {connection.status_detail}
        </p>
      ) : null}
      {connection.saved ? (
        <div className="ai-models">
          <h3>Models</h3>
          {connection.models.length === 0 ? (
            <p className="hint">No models yet. Refresh to ask {label}, or add one below.</p>
          ) : (
            <table>
              <caption className="visually-hidden">{label} models</caption>
              <thead>
                <tr>
                  <th scope="col">Model</th>
                  <th scope="col">Max tokens</th>
                  <th scope="col">Temperature</th>
                  <th scope="col">Timeout (s)</th>
                  <th scope="col">Actions</th>
                </tr>
              </thead>
              <tbody>
                {connection.models.map((model) => (
                  <tr key={model.name}>
                    <th scope="row">
                      {model.name}
                      {model.is_default ? <span className="badge">Default</span> : null}
                    </th>
                    <td>{show(model.max_tokens)}</td>
                    <td>{show(model.temperature)}</td>
                    <td>{show(model.timeout_s)}</td>
                    <td className="row-actions">
                      <Button
                        appearance="stealth"
                        disabled={busy}
                        onClick={() => editModel(model)}
                        label={`Edit ${model.name}`}
                      >
                        Edit
                      </Button>
                      <Button
                        appearance="stealth"
                        disabled={busy || model.is_default}
                        onClick={() =>
                          run(async () => {
                            await setDefaultAiModel(provider, model.name);
                          })
                        }
                        label={`Make ${model.name} the default model`}
                      >
                        Make default
                      </Button>
                      <Button
                        appearance="outline"
                        danger
                        disabled={busy}
                        onClick={() =>
                          run(async () => {
                            await removeAiModel(provider, model.name);
                          })
                        }
                        label={`Remove ${model.name}`}
                      >
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <div className="row actions">
            <Button disabled={busy} onClick={refresh} label={`Refresh ${label} models`}>
              Refresh models
            </Button>
          </div>
          <h4>Add or change a model</h4>
          <div className="row">
            <ComboBox
              label={`${label} model name`}
              value={form.name}
              onChange={changeName}
              options={connection.models.map((model) => model.name)}
              maxLength={128}
            />
            <TextField
              label={`${label} max tokens`}
              value={form.maxTokens}
              onChange={setField('maxTokens')}
            />
            <TextField
              label={`${label} temperature`}
              value={form.temperature}
              onChange={setField('temperature')}
            />
            <TextField
              label={`${label} timeout`}
              value={form.timeout}
              onChange={setField('timeout')}
            />
          </div>
          <p className="hint">
            Max tokens 1 to 1000000, temperature 0 to 2, timeout 1 to 600 seconds. A new model with
            a setting left empty gets Kodalo&apos;s standard for that kind of model; on a saved
            model, empty goes back to the provider&apos;s own.
          </p>
          <div className="row actions">
            <Button
              appearance="accent"
              disabled={busy || !form.name.trim()}
              onClick={saveModel}
              label={`Save ${label} model`}
            >
              Save model
            </Button>
          </div>
        </div>
      ) : null}
    </section>
  );
}
