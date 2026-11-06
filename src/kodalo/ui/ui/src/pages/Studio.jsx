import { useEffect, useState } from 'react';
import {
  getRepository,
  listBrands,
  listRepositories,
  makeIdeas,
  planIdeas,
  readReadme,
} from '../api.js';
import { Button, Select } from '../components/controls.jsx';
import FocusView from './FocusView.jsx';
import IdeasView from './IdeasView.jsx';
import { get } from '../lookup.js';

const STEPS = [
  ['source', 'Source'],
  ['focus', 'Focus'],
  ['ideas', 'Ideas'],
  ['post', 'Post'],
];

/** @param {{ visible: boolean, onOpenRepositories: () => void }} props */
export default function StudioPage({ visible, onOpenRepositories }) {
  const [step, setStep] = useState('source');
  const [repos, setRepos] = useState(/** @type {any[]} */ ([]));
  const [repoId, setRepoId] = useState('');
  const [repo, setRepo] = useState(/** @type {any} */ (null));
  const [readme, setReadme] = useState(/** @type {any} */ (null));
  const [postType, setPostType] = useState('');
  const [focus, setFocus] = useState('');
  const [ideas, setIdeas] = useState(/** @type {any} */ (null));
  const [brands, setBrands] = useState(/** @type {any[]} */ ([]));
  const [brandId, setBrandId] = useState('');
  const [pick, setPick] = useState(/** @type {any} */ (null)); // the chosen idea and hook
  const [plan, setPlan] = useState(/** @type {any} */ (null));
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  // Repositories are added on the Repositories page, so read the list whenever this step shows.
  useEffect(() => {
    if (!visible || step !== 'source') return undefined;
    let alive = true;
    listRepositories().then(
      (list) => {
        if (!alive) return;
        setRepos(list);
        setRepoId((current) =>
          list.some((r) => r.id === current) ? current : (list[0]?.id ?? ''),
        );
      },
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, [visible, step]);

  // The brand is chosen on the Ideas step; read the list when it opens, in case it changed.
  useEffect(() => {
    if (!visible || step !== 'ideas') return undefined;
    let alive = true;
    listBrands().then(
      (list) => {
        if (!alive) return;
        setBrands(list);
        setBrandId((current) =>
          list.some((/** @type {any} */ b) => b.id === current)
            ? current
            : ((list.find((/** @type {any} */ b) => b.is_default) ?? list[0])?.id ?? ''),
        );
      },
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, [visible, step]);

  /** @param {() => Promise<void>} action */
  async function run(action) {
    setBusy(true);
    setError('');
    try {
      await action();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  /**
   * Show what the AI would be sent and ask first. The saved ideas are reused when the choice is
   * the same, unless `refresh` is set.
   * @param {boolean} refresh
   */
  const generateIdeas = (refresh) => {
    const [kind, position] = focus.split(':');
    const item = postType === 'feature' ? get(readme, kind)?.at(Number(position)) : null;
    const name = item ? (item.name ?? item.title) : '';
    const key = `${repo.id}|${postType}|${kind ?? ''}|${name}`;
    if (!refresh && ideas?.key === key) {
      setStep('ideas');
      return Promise.resolve();
    }
    const body = { post_type: postType, kind: item ? kind : '', name };
    return run(async () => {
      setPlan({ ...(await planIdeas(repo.id, body)), key, body });
    });
  };

  const proceedIdeas = () =>
    run(async () => {
      const { key, body } = plan;
      setPlan(null);
      setIdeas({ key, data: await makeIdeas(repo.id, body) });
      setPick(null);
      setStep('ideas');
    });

  const next = () =>
    run(async () => {
      const chosen = await getRepository(repoId);
      setRepo(chosen);
      setReadme(await readReadme(chosen.id, false));
      setIdeas(null); // the ideas were made from the previous analysis
      setPick(null);
      setStep('focus');
    });

  return (
    <section className="studio" aria-labelledby="studio-title">
      <h1 id="studio-title">Studio</h1>
      <p className="hint">Turn a repository into ready-to-post social content.</p>
      <ol className="steps" aria-label="Steps">
        {STEPS.map(([key, label]) => (
          <li key={key} aria-current={step === key ? 'step' : undefined}>
            {label}
          </li>
        ))}
      </ol>

      {step === 'source' ? (
        <>
          <h2>Choose a repository</h2>
          {repos.length === 0 ? (
            <p className="hint">No repositories yet. Add one on the Repositories page.</p>
          ) : (
            <Select label="Repository" value={repoId} onChange={setRepoId}>
              {repos.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.owner}/{r.name}
                </option>
              ))}
            </Select>
          )}
          <p className="hint">
            <button type="button" className="link" onClick={onOpenRepositories}>
              Add or remove repositories
            </button>
          </p>
          <div className="row actions">
            <Button appearance="accent" disabled={busy || !repoId} onClick={next}>
              Next
            </Button>
          </div>
        </>
      ) : null}

      {step === 'focus' && repo ? (
        <FocusView
          postType={postType}
          onChange={(value) => {
            setPostType(value);
            if (value !== 'feature') setFocus('');
          }}
          readme={readme}
          focus={focus}
          onFocus={setFocus}
          busy={busy || plan !== null}
          onNext={() => generateIdeas(false)}
          onBack={() => {
            setFocus(''); // the analysis may be refreshed, so the saved pick could point elsewhere
            setStep('source');
          }}
        />
      ) : null}

      {step === 'ideas' && ideas ? (
        <IdeasView
          ideas={ideas.data}
          busy={busy || plan !== null}
          brands={brands}
          brandId={brandId}
          onBrand={setBrandId}
          pick={pick}
          onPick={setPick}
          onRefresh={() => generateIdeas(true)}
          onNext={() => setStep('post')}
          onBack={() => setStep('focus')}
        />
      ) : null}

      {step === 'post' && ideas && pick ? (
        <>
          <h2>Post</h2>
          <p>
            Chosen idea:{' '}
            {
              ideas.data.post_ideas.find((/** @type {any} */ i) => i.id === pick.idea)
                ?.working_title
            }
          </p>
          <p className="hint">Designing the post comes next.</p>
          <div className="row actions">
            <Button onClick={() => setStep('ideas')}>Back</Button>
          </div>
        </>
      ) : null}

      {plan ? (
        <div role="group" aria-labelledby="ideas-plan-title" className="confirm">
          <h3 id="ideas-plan-title">Send to {plan.label}?</h3>
          <p>
            Kodalo will send what the README analysis saved about {plan.items.join(', ')}, with its
            evidence quotes and the claims to repeat with care. The AI plans a strategy, three
            angles with hooks and five post ideas; each claim is kept only if its quote was sent.
          </p>
          <p>
            It goes to {plan.label} ({plan.model}). About {plan.input_tokens} tokens sent, and at
            most {plan.max_output_tokens} tokens in the answer.
          </p>
          <div className="row actions">
            <Button appearance="accent" disabled={busy} onClick={proceedIdeas}>
              Proceed
            </Button>
            <Button disabled={busy} onClick={() => setPlan(null)}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}

      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
