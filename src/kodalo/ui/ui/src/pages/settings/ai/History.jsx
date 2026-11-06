import { useCallback, useEffect, useRef, useState } from 'react';
import {
  getAiCall,
  getAiHistorySettings,
  getAiUsage,
  listAiHistory,
  purgeAiHistory,
  saveAiHistorySettings,
} from '../../../api.js';
import { Button, NumberField, Select, Switch } from '../../../components/controls.jsx';
import { saveText } from '../../../download.js';

/** @typedef {{ id: string, created_at: string, title: string, purpose: string, provider: string, model: string, status: string, error: string, input_tokens: number, output_tokens: number, has_text: boolean }} AiCall */
/** @typedef {AiCall & { prompt_text: string | null, reply_text: string | null }} AiCallDetail */
/** @typedef {{ calls: number, input_tokens: number, output_tokens: number, rows: { provider: string, model: string, calls: number, input_tokens: number, output_tokens: number }[], days: { day: string, input_tokens: number, output_tokens: number }[] }} AiUsage */

const PERIODS = [
  ['day', 'Last day'],
  ['week', 'Last week'],
  ['month', 'Last month'],
  ['year', 'Last year'],
  ['all', 'All time'],
  ['custom', 'Custom'],
];
const PROVIDERS = new Map([
  ['claude_api', 'Claude API'],
  ['claude_code', 'Claude Code'],
  ['chatgpt_api', 'ChatGPT API'],
  ['gemini_api', 'Gemini API'],
]);
const PURPOSES = new Map([
  ['palette', 'Palette'],
  ['studio', 'Studio'],
  ['connection_test', 'Connection test'],
]);
const PAGE = 25;
const CHART = { width: 640, height: 160, left: 8, bottom: 4 };

/** @param {string} id */
const providerName = (id) => PROVIDERS.get(id) ?? id;
/** @param {string} value */
const when = (value) => new Date(value).toLocaleString();
/** @param {number} value */
const count = (value) => value.toLocaleString();

/**
 * Tokens per day as stacked bars: what was sent (input) below, what came back (output) above.
 * @param {{ days: AiUsage['days'] }} props
 */
function TokenChart({ days }) {
  if (days.length === 0) return <p className="hint">No tokens were used in this period.</p>;
  const most = Math.max(...days.map((day) => day.input_tokens + day.output_tokens), 1);
  const room = CHART.height - CHART.bottom;
  const slot = (CHART.width - CHART.left) / days.length;
  const wide = Math.max(Math.min(slot * 0.7, 48), 2);
  const first = days[0].day;
  const last = days[days.length - 1].day;
  const label = `Tokens per day from ${first} to ${last}. Most in one day: ${count(most)}.`;
  return (
    <figure className="chart">
      <svg viewBox={`0 0 ${CHART.width} ${CHART.height + 18}`} role="img" aria-label={label}>
        {days.map((day, index) => {
          const x = CHART.left + index * slot + (slot - wide) / 2;
          const sent = (day.input_tokens / most) * room;
          const received = (day.output_tokens / most) * room;
          return (
            <g key={day.day}>
              <title>{`${day.day}: ${count(day.input_tokens)} in, ${count(day.output_tokens)} out`}</title>
              <rect className="bar-in" x={x} y={room - sent} width={wide} height={sent} />
              <rect
                className="bar-out"
                x={x}
                y={room - sent - received}
                width={wide}
                height={received}
              />
            </g>
          );
        })}
        <text className="axis" x={CHART.left} y={CHART.height + 12}>
          {first}
        </text>
        <text className="axis" x={CHART.width} y={CHART.height + 12} textAnchor="end">
          {last}
        </text>
      </svg>
      <figcaption>
        <span className="key key-in" /> Tokens sent <span className="key key-out" /> Tokens received
      </figcaption>
    </figure>
  );
}

/** One entry with what was sent and what came back, when the text was kept.
 * @param {{ call: AiCallDetail, onClose: () => void }} props */
function CallDetails({ call, onClose }) {
  const heading = useRef(/** @type {HTMLHeadingElement | null} */ (null));
  const [copied, setCopied] = useState('');

  useEffect(() => {
    heading.current?.focus();
    /** @param {KeyboardEvent} event */
    const onKey = (event) => event.key === 'Escape' && onClose();
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  /** @param {string} name @param {string | null} text */
  async function copy(name, text) {
    try {
      await navigator.clipboard.writeText(text ?? '');
      setCopied(`Copied the ${name}.`);
    } catch {
      setCopied('Copying is not available here. Select the text and copy it instead.');
    }
  }

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="call-title" className="dialog">
      <div className="dialog-head">
        <h3 id="call-title" ref={heading} tabIndex={-1}>
          {call.title}
        </h3>
        <Button appearance="stealth" onClick={onClose} label="Close dialog" title="Close dialog">
          <i className="bi bi-x-lg" aria-hidden="true" />
        </Button>
      </div>
      <dl className="facts">
        <dt>When</dt>
        <dd>{when(call.created_at)}</dd>
        <dt>Purpose</dt>
        <dd>{PURPOSES.get(call.purpose) ?? call.purpose}</dd>
        <dt>Connection</dt>
        <dd>{providerName(call.provider)}</dd>
        <dt>Model</dt>
        <dd>{call.model || '-'}</dd>
        <dt>Status</dt>
        <dd>{call.status === 'ok' ? 'Success' : `Failed: ${call.error}`}</dd>
        <dt>Tokens</dt>
        <dd>
          {count(call.input_tokens)} sent, {count(call.output_tokens)} received
        </dd>
      </dl>
      {call.has_text ? (
        <>
          <div className="dialog-section">
            <h4>Sent</h4>
            <Button
              onClick={() => copy('input', call.prompt_text)}
              label="Copy input"
              title="Copy input"
            >
              <i className="bi bi-copy" aria-hidden="true" />
            </Button>
          </div>
          <pre className="text">{call.prompt_text ?? 'Not kept.'}</pre>
          <div className="dialog-section">
            <h4>Received</h4>
            <Button
              onClick={() => copy('output', call.reply_text)}
              label="Copy output"
              title="Copy output"
            >
              <i className="bi bi-copy" aria-hidden="true" />
            </Button>
          </div>
          <pre className="text">{call.reply_text ?? 'Nothing came back.'}</pre>
        </>
      ) : (
        <p className="hint">
          The text was not kept for this entry. Turn on &quot;Keep the text of prompts and
          answers&quot; to see it for new calls.
        </p>
      )}
      {copied ? (
        <p role="status" className="notice">
          {copied}
        </p>
      ) : null}
      <div className="row actions end">
        <Button appearance="accent" onClick={onClose} label="Close" title="Close">
          <i className="bi bi-x-lg" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

/** How the AI history is kept: whether the text is stored and for how long. */
export function AiHistorySettings() {
  const [store, setStore] = useState(false);
  const [days, setDays] = useState(90);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getAiHistorySettings().then(
      (value) => {
        setStore(value.store_text);
        setDays(value.retention_days);
      },
      (failure) => setError(failure.message),
    );
  }, []);

  async function save() {
    setBusy(true);
    setError('');
    setSaved(false);
    try {
      const value = await saveAiHistorySettings({ store_text: store, retention_days: days });
      setStore(value.store_text);
      setDays(value.retention_days);
      setSaved(true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="ai-history">
      <h2>Keeping the history</h2>
      <p className="hint">
        Every call to an AI model is kept with the tokens it used. Entries older than the number of
        days below are removed automatically when Kodalo starts.
      </p>
      <Switch label="Keep the text of prompts and answers" checked={store} onChange={setStore} />
      <NumberField
        label="Remove entries after (days)"
        value={days}
        min={0}
        max={3650}
        onChange={setDays}
        hint="0 keeps entries until you purge them."
      />
      <div className="row actions">
        <Button
          appearance="accent"
          disabled={busy}
          onClick={save}
          label="Save history settings"
          title="Save history settings"
        >
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
    </div>
  );
}

/** One row of the export: what the history table shows, without the prompt and answer text.
 * @param {AiCall} call */
const exportRow = (call) => ({
  date: call.created_at,
  title: call.title,
  purpose: PURPOSES.get(call.purpose) ?? call.purpose,
  connection: providerName(call.provider),
  model: call.model,
  status: call.status === 'ok' ? 'Success' : 'Failed',
  error: call.error,
  tokens_sent: call.input_tokens,
  tokens_received: call.output_tokens,
});

/** @param {unknown} value a cell; text that a spreadsheet could run as a formula is made safe */
function csvCell(value) {
  const text = String(value ?? '');
  const safe = /^[=+\-@\t\r]/.test(text) ? `'${text}` : text;
  return /[",\n\r]/.test(safe) ? `"${safe.replaceAll('"', '""')}"` : safe;
}

/** @param {ReturnType<typeof exportRow>[]} rows */
function toCsv(rows) {
  const columns = Object.keys(exportRow(/** @type {AiCall} */ ({ created_at: '' })));
  const lines = rows.map((row) => Object.values(row).map(csvCell).join(','));
  return `${[columns.join(','), ...lines].join('\r\n')}\r\n`;
}

const EXPORT_TYPES = {
  csv: { mime: 'text/csv', label: 'CSV files (*.csv)' },
  json: { mime: 'application/json', label: 'JSON files (*.json)' },
};

/** The AI history: the tokens used and every call that was made. */
export default function AiHistory() {
  const [period, setPeriod] = useState('week');
  const [start, setStart] = useState('');
  const [end, setEnd] = useState('');
  const [offset, setOffset] = useState(0);
  const [format, setFormat] = useState('csv');
  const [usage, setUsage] = useState(/** @type {AiUsage | null} */ (null));
  const [page, setPage] = useState(/** @type {{ total: number, items: AiCall[] } | null} */ (null));
  const [detail, setDetail] = useState(/** @type {AiCallDetail | null} */ (null));
  const [confirming, setConfirming] = useState(false);
  const [notice, setNotice] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [version, setVersion] = useState(0);

  const waiting = period === 'custom' && !start && !end;

  useEffect(() => {
    if (waiting) return undefined;
    let alive = true;
    const range = { period, start, end };
    Promise.all([getAiUsage(range), listAiHistory({ ...range, limit: PAGE, offset })]).then(
      ([counts, list]) => {
        if (!alive) return;
        setUsage(counts);
        setPage(list);
        setError('');
      },
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, [period, start, end, offset, waiting, version]);

  /** @param {() => Promise<void>} action */
  async function run(action) {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  /** A filter changed: start again from the newest entries. @param {(value: string) => void} set */
  const filter = (set) => (/** @type {string} */ value) => {
    set(value);
    setOffset(0);
  };

  /** Every entry of the chosen period, not only the page on screen. */
  const exportHistory = () =>
    run(async () => {
      const range = { period, start, end };
      /** @type {AiCall[]} */
      const items = [];
      for (;;) {
        const list = await listAiHistory({ ...range, limit: 200, offset: items.length });
        items.push(...list.items);
        if (list.items.length === 0 || items.length >= list.total) break;
      }
      const rows = items.map(exportRow);
      const text = format === 'csv' ? toCsv(rows) : JSON.stringify(rows, null, 2);
      const type = format === 'csv' ? EXPORT_TYPES.csv : EXPORT_TYPES.json;
      if (await saveText(text, `ai-history.${format}`, type)) {
        setNotice(`Exported ${count(items.length)} entries.`);
      }
    });

  /** @param {string} id */
  const open = (id) =>
    run(async () => {
      setDetail(await getAiCall(id));
    });

  const purge = () =>
    run(async () => {
      const result = await purgeAiHistory();
      setConfirming(false);
      setOffset(0);
      setVersion((value) => value + 1);
      setNotice(`Removed ${count(result.deleted)} entries.`);
    });

  const closeDetail = useCallback(() => setDetail(null), []);
  const shown = page ? page.items.length : 0;
  const total = page ? page.total : 0;

  return (
    <div className="ai-history">
      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
      <h2>Period</h2>
      <div className="row period">
        <Select label="Show" value={period} onChange={filter(setPeriod)}>
          {PERIODS.map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </Select>
        {period === 'custom' ? (
          <>
            <label className="field select">
              <span>From</span>
              <input
                type="date"
                value={start}
                max={end || undefined}
                onChange={(event) => filter(setStart)(event.target.value)}
              />
            </label>
            <label className="field select">
              <span>To</span>
              <input
                type="date"
                value={end}
                min={start || undefined}
                onChange={(event) => filter(setEnd)(event.target.value)}
              />
            </label>
          </>
        ) : null}
        <div className="row actions period-tools">
          <Select label="Export as" value={format} onChange={setFormat}>
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
          </Select>
          <Button
            disabled={busy || waiting}
            onClick={exportHistory}
            label="Export history"
            title="Export history"
          >
            <i className="bi bi-box-arrow-up" aria-hidden="true" />
          </Button>
          {confirming ? null : (
            <Button
              danger
              disabled={busy}
              onClick={() => setConfirming(true)}
              label="Purge history"
              title="Purge history"
            >
              <i className="bi bi-trash" aria-hidden="true" />
            </Button>
          )}
        </div>
      </div>
      {waiting ? <p className="hint">Choose a first day, a last day, or both.</p> : null}
      {confirming ? (
        <div role="group" aria-labelledby="purge-title" className="confirm">
          <h3 id="purge-title">Remove the whole AI history?</h3>
          <p>Every entry and the token totals will be removed. This cannot be undone.</p>
          <div className="row actions end">
            <Button
              disabled={busy}
              onClick={() => setConfirming(false)}
              label="Cancel"
              title="Cancel"
            >
              <i className="bi bi-x-lg" aria-hidden="true" />
            </Button>
            <Button
              danger
              disabled={busy}
              onClick={purge}
              label="Yes, purge everything"
              title="Yes, purge everything"
            >
              <i className="bi bi-check-lg" aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : null}
      {notice ? (
        <p role="status" className="notice">
          {notice}
        </p>
      ) : null}

      <h2>Token usage</h2>
      {usage ? (
        <>
          <table className="checks">
            <caption className="visually-hidden">Token usage per connection and model</caption>
            <thead>
              <tr>
                <th scope="col">Connection</th>
                <th scope="col">Model</th>
                <th scope="col" className="num">
                  Calls
                </th>
                <th scope="col" className="num">
                  Tokens sent
                </th>
                <th scope="col" className="num">
                  Tokens received
                </th>
                <th scope="col" className="num">
                  Total
                </th>
              </tr>
            </thead>
            <tbody>
              {usage.rows.length === 0 ? (
                <tr>
                  <td colSpan={6}>Nothing was used in this period.</td>
                </tr>
              ) : (
                usage.rows.map((row) => (
                  <tr key={`${row.provider}/${row.model}`}>
                    <th scope="row">{providerName(row.provider)}</th>
                    <td>{row.model || '-'}</td>
                    <td className="num">{count(row.calls)}</td>
                    <td className="num">{count(row.input_tokens)}</td>
                    <td className="num">{count(row.output_tokens)}</td>
                    <td className="num">{count(row.input_tokens + row.output_tokens)}</td>
                  </tr>
                ))
              )}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row">All</th>
                <td />
                <td className="num">{count(usage.calls)}</td>
                <td className="num">{count(usage.input_tokens)}</td>
                <td className="num">{count(usage.output_tokens)}</td>
                <td className="num">{count(usage.input_tokens + usage.output_tokens)}</td>
              </tr>
            </tfoot>
          </table>
          <TokenChart days={usage.days} />
        </>
      ) : (
        <p>Loading…</p>
      )}

      <h2>History</h2>
      {page ? (
        <>
          <table className="checks">
            <caption className="visually-hidden">AI calls, newest first</caption>
            <thead>
              <tr>
                <th scope="col">Date and time</th>
                <th scope="col">Title</th>
                <th scope="col">Purpose</th>
                <th scope="col">Connection</th>
                <th scope="col">Model</th>
                <th scope="col">Status</th>
                <th scope="col" className="num">
                  Sent
                </th>
                <th scope="col" className="num">
                  Received
                </th>
              </tr>
            </thead>
            <tbody>
              {page.items.length === 0 ? (
                <tr>
                  <td colSpan={8}>No calls in this period.</td>
                </tr>
              ) : (
                page.items.map((call) => (
                  <tr key={call.id}>
                    <td>{when(call.created_at)}</td>
                    <th scope="row">
                      <button
                        type="button"
                        className="link"
                        aria-label={`Details of ${call.title}, ${when(call.created_at)}`}
                        onClick={() => open(call.id)}
                      >
                        {call.title}
                      </button>
                    </th>
                    <td>{PURPOSES.get(call.purpose) ?? call.purpose}</td>
                    <td>{providerName(call.provider)}</td>
                    <td>{call.model || '-'}</td>
                    <td>{call.status === 'ok' ? 'Success' : 'Failed'}</td>
                    <td className="num">{count(call.input_tokens)}</td>
                    <td className="num">{count(call.output_tokens)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
          <div className="row actions">
            <Button
              disabled={busy || offset === 0}
              onClick={() => setOffset(offset - PAGE)}
              label="Newer"
              title="Newer"
            >
              <i className="bi bi-chevron-left" aria-hidden="true" />
            </Button>
            <span role="status">
              {total === 0 ? '0 entries' : `${offset + 1} to ${offset + shown} of ${count(total)}`}
            </span>
            <Button
              disabled={busy || offset + PAGE >= total}
              onClick={() => setOffset(offset + PAGE)}
              label="Older"
              title="Older"
            >
              <i className="bi bi-chevron-right" aria-hidden="true" />
            </Button>
          </div>
        </>
      ) : (
        <p>Loading…</p>
      )}
      {detail ? <CallDetails call={detail} onClose={closeDetail} /> : null}
    </div>
  );
}
