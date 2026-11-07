import { useState } from 'react';
import Appearance from './Appearance.jsx';
import AiConnections from './ai/Connections.jsx';
import AiHistory, { AiHistorySettings } from './ai/History.jsx';
import AiIdeaCount from './ai/IdeaCount.jsx';
import AiTaskModels from './ai/TaskModels.jsx';
import GitHub from './GitHub.jsx';
import Platforms from './platforms/Platforms.jsx';

const TABS = [
  ['github', 'GitHub'],
  ['ai', 'AI'],
  ['platforms', 'Platforms'],
  ['appearance', 'Appearance'],
];

export default function SettingsPage() {
  const [tab, setTab] = useState('github');
  const [historyOpen, setHistoryOpen] = useState(false);
  const [modelsOpen, setModelsOpen] = useState(false);
  const [ideasOpen, setIdeasOpen] = useState(false);

  return (
    <div className="settings">
      <h1>Settings</h1>
      <p>Choose how Kodalo connects to the services it uses.</p>
      <div role="tablist" aria-label="Settings" className="tabs">
        {TABS.map(([key, label]) => (
          <button
            key={key}
            type="button"
            role="tab"
            id={`tab-${key}`}
            aria-selected={tab === key}
            aria-controls={`panel-${key}`}
            onClick={() => setTab(key)}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === 'appearance' ? <Appearance /> : null}
      {tab === 'platforms' ? <Platforms /> : null}
      {tab === 'ai' ? (
        <section className="panel" role="tabpanel" id="panel-ai" aria-labelledby="tab-ai">
          <AiConnections />
          <AiHistorySettings />
          <details
            className="accordion"
            open={modelsOpen}
            onToggle={(event) => setModelsOpen(event.currentTarget.open)}
          >
            <summary>Models per job</summary>
            {modelsOpen ? <AiTaskModels /> : null}
          </details>
          <details
            className="accordion"
            open={ideasOpen}
            onToggle={(event) => setIdeasOpen(event.currentTarget.open)}
          >
            <summary>Studio post ideas</summary>
            {ideasOpen ? <AiIdeaCount /> : null}
          </details>
          <details
            className="accordion"
            open={historyOpen}
            onToggle={(event) => setHistoryOpen(event.currentTarget.open)}
          >
            <summary>View AI history</summary>
            {historyOpen ? <AiHistory /> : null}
          </details>
        </section>
      ) : null}
      {tab === 'github' ? <GitHub /> : null}
    </div>
  );
}
