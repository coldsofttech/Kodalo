import { useEffect, useState } from 'react';
import { getLogSettings, saveLogSettings } from '../../libs/api.js';
import { Button, NumberField, Select } from '../../components/controls.jsx';
import { useSavedValues } from '../../libs/unsaved.js';

const LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

/** How much Kodalo logs and for how long it keeps the log files. */
export default function Logs() {
  const [level, setLevel] = useState('INFO');
  const [days, setDays] = useState(90);
  const [folder, setFolder] = useState('');
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const markSaved = useSavedValues({ level, days });

  useEffect(() => {
    let alive = true;
    getLogSettings().then(
      (logs) => {
        if (!alive) return;
        setLevel(logs.level);
        setDays(logs.retention_days);
        setFolder(logs.folder);
        markSaved({ level: logs.level, days: logs.retention_days });
      },
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, [markSaved]);

  async function save() {
    setBusy(true);
    setError('');
    setSaved(false);
    try {
      const result = await saveLogSettings({ level, retention_days: days });
      setLevel(result.level);
      setDays(result.retention_days);
      markSaved({ level: result.level, days: result.retention_days });
      setSaved(true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" role="tabpanel" id="panel-logs" aria-labelledby="tab-logs">
      <Select label="Log level" value={level} onChange={setLevel}>
        {LEVELS.map((value) => (
          <option key={value} value={value}>
            {value === 'INFO' ? 'INFO (default)' : value}
          </option>
        ))}
      </Select>
      <NumberField
        label="Keep logs for (days)"
        value={days}
        min={1}
        max={3650}
        onChange={setDays}
        hint="Older log files are deleted. Default: 90 days."
      />
      {folder ? <p className="hint">Logs are written to {folder}</p> : null}
      <div className="row actions">
        <Button appearance="accent" label="Save" title="Save" disabled={busy} onClick={save}>
          <i className="bi bi-floppy" aria-hidden="true" />
        </Button>
      </div>
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
      {saved ? (
        <p role="status" className="notice">
          Saved.
        </p>
      ) : null}
    </section>
  );
}
