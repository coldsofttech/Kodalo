import { useEffect, useState } from 'react';
import {
  getCopy,
  getDesign,
  getIdeas,
  getReadme,
  getRepository,
  listBrands,
  listRepositories,
  makeCopy,
  makeDesign,
  makeIdeas,
  planCopy,
  planDesign,
  planIdeas,
  saveCopy,
} from '../../libs/api.js';
import AiOverlay from '../../components/AiOverlay.jsx';
import { Button, Select } from '../../components/controls.jsx';
import DesignView from './DesignView.jsx';
import FocusView from './FocusView.jsx';
import IdeasView from './IdeasView.jsx';
import PostView from './PostView.jsx';
import { get } from '../../libs/lookup.js';

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
  const [copy, setCopy] = useState(/** @type {any} */ (null)); // the written post and its version
  const [design, setDesign] = useState(/** @type {any} */ (null)); // how its slides are laid out
  const [error, setError] = useState('');
  const [generating, setGenerating] = useState(''); // shown over the page while the AI works
  const [setup, setSetup] = useState(''); // what the chosen repository still needs
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
    setSetup('');
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
      if (!refresh) {
        const saved = await getIdeas(repo.id, body).catch(() => null); // 404: none made yet
        if (saved) {
          setIdeas({ key, body, data: saved });
          setPick(null);
          setStep('ideas');
          return;
        }
      }
      setPlan({ ...(await planIdeas(repo.id, body)), key, body, kind: 'ideas' });
    });
  };

  const proceedIdeas = () =>
    run(async () => {
      const { key, body } = plan;
      setPlan(null);
      setGenerating('Planning the strategy, angles and post ideas…');
      try {
        setIdeas({ key, body, data: await makeIdeas(repo.id, body) });
      } finally {
        setGenerating('');
      }
      setPick(null);
      setStep('ideas');
    });

  /** @param {any} data */
  const showCopy = (data) => {
    setCopy((current) => ({ version: (current?.version ?? 0) + 1, data }));
    setStep('post');
  };

  const copyRequest = () => ({
    brand_id: brandId,
    ...ideas.body,
    idea_id: pick.idea,
    hook_id: pick.hook,
  });

  /**
   * Show the saved copy of the chosen idea, or ask first before the AI writes it.
   * @param {boolean} refresh
   */
  const writeCopy = (refresh) =>
    run(async () => {
      const body = copyRequest();
      if (!refresh) {
        const saved = await getCopy(repo.id, body).catch((failure) => {
          if (failure?.status === 404) return null; // none written yet
          throw failure;
        });
        if (saved) {
          showCopy(saved);
          return;
        }
      }
      setPlan({ ...(await planCopy(repo.id, body)), body, kind: 'copy' });
    });

  const proceedCopy = () =>
    run(async () => {
      const { body } = plan;
      setPlan(null);
      setGenerating('Writing the slides, caption and hashtags…');
      try {
        showCopy(await makeCopy(repo.id, body));
      } finally {
        setGenerating('');
      }
    });

  /** @param {any} data */
  const showDesign = (data) => {
    setDesign(data);
    setStep('design');
  };

  const designRequest = () => ({
    brand_id: brandId,
    ...ideas.body,
    idea_id: copy.data.idea_id,
    hook_id: copy.data.hook_id,
  });

  /**
   * Show the saved design of the written post, or ask first before the AI makes it.
   * @param {boolean} refresh
   */
  const writeDesign = (refresh) =>
    run(async () => {
      const body = designRequest();
      if (!refresh) {
        const saved = await getDesign(repo.id, body).catch((failure) => {
          if (failure?.status === 404) return null; // none made yet
          throw failure;
        });
        if (saved) {
          showDesign(saved);
          return;
        }
      }
      setPlan({ ...(await planDesign(repo.id, body)), body, kind: 'design' });
    });

  const proceedDesign = () =>
    run(async () => {
      const { body } = plan;
      setPlan(null);
      setGenerating('Designing the slides…');
      try {
        showDesign(await makeDesign(repo.id, body));
      } finally {
        setGenerating('');
      }
    });

  /** @param {object} edits */
  const saveEdits = (edits) =>
    run(async () => {
      showCopy(await saveCopy(repo.id, { ...copyRequest(), hook_id: copy.data.hook_id, ...edits }));
    });

  const next = () =>
    run(async () => {
      const chosen = await getRepository(repoId);
      const saved = await getReadme(chosen.id).catch(() => null); // 404: not analysed yet
      const missing = [];
      if (!chosen.manifests?.length) missing.push('manifests');
      if (!chosen.frameworks?.length && !chosen.tooling?.length) missing.push('frameworks');
      if (!saved?.features?.length) missing.push('features (README analysis with AI)');
      if (!saved?.use_cases_at) missing.push('use cases (README analysis with AI)');
      if (missing.length > 0) {
        setSetup(
          `${chosen.owner}/${chosen.name} is not fully set up yet. Missing: ${missing.join(', ')}.`,
        );
        return;
      }
      setRepo(chosen);
      setReadme(saved);
      setIdeas(null); // the ideas were made from the previous analysis
      setPick(null);
      setStep('focus');
    });

  const working = busy || plan !== null;
  const canNext =
    (step === 'source' && !!repoId) ||
    (step === 'focus' && !!postType && (postType !== 'feature' || !!focus)) ||
    (step === 'ideas' && !!pick) ||
    (step === 'post' && !!copy);

  const goNext = () => {
    if (step === 'source') return next();
    if (step === 'focus') return generateIdeas(false);
    if (step === 'ideas') return writeCopy(false);
    if (step === 'post') return writeDesign(false);
    return undefined;
  };

  const goBack = () => {
    if (step === 'focus') {
      setFocus(''); // the analysis may be refreshed, so the saved pick could point elsewhere
      setStep('source');
    } else if (step === 'ideas') {
      setStep('focus');
    } else if (step === 'post') {
      setStep('ideas');
    } else if (step === 'design') {
      setStep('post');
    }
  };

  const goHome = () => {
    setFocus('');
    setPick(null);
    setCopy(null);
    setDesign(null);
    setStep('source');
  };

  /** Ask the AI again for what the current step shows. */
  const refresh = () => {
    if (step === 'design') return writeDesign(true);
    return step === 'post' ? writeCopy(true) : generateIdeas(true);
  };

  return (
    <section className="studio" aria-labelledby="studio-title">
      {generating ? <AiOverlay message={generating} /> : null}
      <div className="page-head">
        <h1 id="studio-title">
          {repo && step !== 'source' ? `${repo.owner}/${repo.name}` : 'Studio'}
        </h1>
        <div className="page-home">
          {step === 'ideas' || step === 'post' || step === 'design' ? (
            <Button
              className="ai-button"
              label="Refresh with AI"
              title="Refresh with AI"
              disabled={working}
              onClick={refresh}
            >
              <i className="bi bi-stars" aria-hidden="true" />
            </Button>
          ) : null}
          <Button
            label="Back"
            title="Back"
            disabled={working || step === 'source'}
            onClick={goBack}
          >
            <i className="bi bi-arrow-left" aria-hidden="true" />
          </Button>
          <Button label="Next" title="Next" disabled={working || !canNext} onClick={goNext}>
            <i className="bi bi-arrow-right" aria-hidden="true" />
          </Button>
          <Button
            className="page-home-end"
            label="Studio home"
            title="Studio home"
            disabled={working}
            onClick={goHome}
          >
            <i className="bi bi-house" aria-hidden="true" />
          </Button>
        </div>
      </div>
      {repo && step !== 'source' ? (
        repo.description ? (
          <p className="hint">{repo.description}</p>
        ) : null
      ) : (
        <p className="hint">Turn a repository into ready-to-post social content.</p>
      )}

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
        />
      ) : null}

      {step === 'ideas' && ideas ? (
        <IdeasView
          ideas={ideas.data}
          brands={brands}
          brandId={brandId}
          onBrand={setBrandId}
          pick={pick}
          onPick={setPick}
        />
      ) : null}

      {step === 'post' && copy ? (
        <PostView copy={copy.data} busy={working} onSave={saveEdits} />
      ) : null}

      {step === 'design' && design && copy ? (
        <DesignView
          design={design}
          copy={copy.data}
          brand={brands.find((/** @type {any} */ b) => b.id === brandId)}
          repo={repo}
          request={designRequest()}
        />
      ) : null}

      {plan ? (
        <div role="group" aria-labelledby="ideas-plan-title" className="confirm">
          <h3 id="ideas-plan-title">Send to {plan.label}?</h3>
          {plan.kind === 'design' ? (
            <>
              <p>
                Kodalo will send the written slides (headlines, text and what each picture should
                show), the pictures and icons you allowed in Settings, and the size of the brand's
                canvas. The AI chooses a template, alignment, picture and icon for each slide; it
                writes no text.
              </p>
              {plan.writes_html ? (
                <p>
                  Use AI-powered templates/styles is on, so the AI writes each slide as HTML and
                  CSS. The answer is much longer, so this costs more than the fixed templates. It
                  still writes no text of its own, and a slide that changes the words is not used.
                </p>
              ) : null}
              {plan.sees_social_preview ? (
                <p>
                  The repository has no icon file, so its social preview image is sent too, once, to
                  find its logo.
                </p>
              ) : null}
            </>
          ) : plan.kind === 'copy' ? (
            <p>
              Kodalo will send the chosen post idea ({plan.items.join(', ')}) with its hook, the
              claims it may state and the claims to avoid. The AI writes the slides, a caption with
              an alternative opening, alt text and hashtags.
            </p>
          ) : (
            <p>
              Kodalo will send what the README analysis saved about {plan.items.join(', ')}, with
              its evidence quotes and the claims to repeat with care. The AI plans a strategy, three
              angles with hooks and five post ideas; each claim is kept only if its quote was sent.
            </p>
          )}
          <p>
            It goes to {plan.label} ({plan.model}). About {plan.input_tokens} tokens sent, and at
            most {plan.max_output_tokens} tokens in the answer.
          </p>
          <div className="row actions">
            <Button
              appearance="accent"
              label="Proceed"
              title="Proceed"
              disabled={busy}
              onClick={
                plan.kind === 'design'
                  ? proceedDesign
                  : plan.kind === 'copy'
                    ? proceedCopy
                    : proceedIdeas
              }
            >
              <i className="bi bi-check-lg" aria-hidden="true" />
            </Button>
            <Button label="Cancel" title="Cancel" disabled={busy} onClick={() => setPlan(null)}>
              <i className="bi bi-x-lg" aria-hidden="true" />
            </Button>
          </div>
        </div>
      ) : null}

      {setup ? (
        <p role="alert" className="alert">
          {setup} Set it up on the Repositories page first.{' '}
          <button type="button" className="link" onClick={onOpenRepositories}>
            Open Repositories
          </button>
        </p>
      ) : null}

      {error ? (
        <p role="alert" className="alert">
          {error}
        </p>
      ) : null}
    </section>
  );
}
