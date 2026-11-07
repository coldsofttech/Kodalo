import { useEffect, useState } from 'react';
import { getPlatformSettings, savePlatformSettings } from '../../../libs/api.js';
import { Button, NumberField, Select, Switch, TextField } from '../../../components/controls.jsx';
import { useSavedValues } from '../../../libs/unsaved.js';
import InstagramConnection from './InstagramConnection.jsx';

const PLATFORM_CHOICES = [
  ['instagram', 'Instagram'],
  ['custom', 'Custom'],
];
const NO_VISUALS = {
  use_social_preview: false,
  use_repo_icon: false,
  use_icons: false,
  build_custom_images: false,
  use_ai_templates: false,
};

/** @param {any} settings */
const visualsOf = (settings) => ({
  use_social_preview: settings.use_social_preview,
  use_repo_icon: settings.use_repo_icon,
  use_icons: settings.use_icons,
  build_custom_images: settings.build_custom_images,
  use_ai_templates: settings.use_ai_templates,
});

/** The form's values as they are when they match `settings`. @param {any} settings */
const savedOf = (settings) => ({
  count: settings.hashtag_count,
  tags: settings.default_hashtags.join(' '),
  visuals: visualsOf(settings),
});

/** How many hashtags a post gets on a platform, and the ones every post carries. */
export default function Platforms() {
  const [platform, setPlatform] = useState('instagram');
  const [count, setCount] = useState(5);
  const [tags, setTags] = useState('');
  const [visuals, setVisuals] = useState(NO_VISUALS);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const markSaved = useSavedValues({ count, tags, visuals });

  useEffect(() => {
    let alive = true;
    getPlatformSettings(platform).then(
      (settings) => {
        if (!alive) return;
        setCount(settings.hashtag_count);
        setTags(settings.default_hashtags.join(' '));
        setVisuals(visualsOf(settings));
        markSaved(savedOf(settings));
      },
      (failure) => alive && setError(failure.message),
    );
    return () => {
      alive = false;
    };
  }, [platform, markSaved]);

  async function save() {
    setBusy(true);
    setError('');
    setSaved(false);
    try {
      const result = await savePlatformSettings(platform, {
        hashtag_count: count,
        default_hashtags: tags.split(/[\s,]+/).filter(Boolean),
        ...visuals,
      });
      setCount(result.hashtag_count);
      setTags(result.default_hashtags.join(' '));
      setVisuals(visualsOf(result));
      markSaved(savedOf(result));
      setSaved(true);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : 'Something went wrong.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel" role="tabpanel" id="panel-platforms" aria-labelledby="tab-platforms">
      <Select label="Platform" value={platform} onChange={setPlatform}>
        {PLATFORM_CHOICES.map(([value, label]) => (
          <option key={value} value={value}>
            {label}
          </option>
        ))}
      </Select>
      {platform === 'instagram' ? <InstagramConnection /> : null}
      <NumberField
        label="Hashtags per post"
        value={count}
        min={0}
        max={30}
        hint="The most a post gets, the default hashtags included. Instagram allows up to 30."
        onChange={setCount}
      />
      <TextField
        label="Default hashtags"
        value={tags}
        maxLength={600}
        hint="Added to every post, before the ones the AI writes. Separate them with spaces."
        onChange={setTags}
      />
      <p className="hint">What the designer may use when it lays out a post.</p>
      <div className="switch-grid">
        <Switch
          label="Use social preview"
          checked={visuals.use_social_preview}
          onChange={(value) => setVisuals((current) => ({ ...current, use_social_preview: value }))}
        />
        <Switch
          label="Use repo icon"
          checked={visuals.use_repo_icon}
          onChange={(value) => setVisuals((current) => ({ ...current, use_repo_icon: value }))}
        />
        <Switch
          label="Use icons"
          checked={visuals.use_icons}
          onChange={(value) => setVisuals((current) => ({ ...current, use_icons: value }))}
        />
        <Switch
          label="Build custom images as needed"
          checked={visuals.build_custom_images}
          onChange={(value) =>
            setVisuals((current) => ({ ...current, build_custom_images: value }))
          }
        />
        <Switch
          label="Use AI-powered templates/styles"
          checked={visuals.use_ai_templates}
          onChange={(value) => setVisuals((current) => ({ ...current, use_ai_templates: value }))}
        />
      </div>
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
