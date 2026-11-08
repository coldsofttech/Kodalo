import { Select } from '../../components/controls.jsx';
import { get } from '../../libs/lookup.js';

export const POST_TYPES = [
  {
    value: 'tool',
    label: 'Tool / Utility post',
    hint: 'Introduce the whole tool, utility or library at a high level.',
  },
  {
    value: 'feature',
    label: 'Feature post',
    hint: 'Highlight one feature, use-case or capability.',
  },
];

const IMPORTANCE = ['headline', 'supporting', 'minor'];

/** The groups of the dropdown, each with the key of its list in the README analysis. */
const FOCUS_GROUPS = [
  ['features', 'Features', 'name'],
  ['use_cases', 'Use cases', 'title'],
  ['capabilities', 'Capabilities', 'name'],
];

/**
 * @param {{ postType: string, onChange: (value: string) => void, readme: any, focus: string,
 *   onFocus: (value: string) => void }} props
 */
export default function FocusView({ postType, onChange, readme, focus, onFocus }) {
  const groups = FOCUS_GROUPS.map(([key, label, field]) => ({
    key,
    label,
    items: (get(readme, key) ?? [])
      .map((/** @type {any} */ item, /** @type {number} */ index) => ({
        value: `${key}:${index}`,
        text: get(item, field),
        rank: key === 'features' ? Math.max(0, IMPORTANCE.indexOf(item.importance)) : 0,
      }))
      .sort((a, b) => a.rank - b.rank), // headline features first; the sort is stable
  })).filter((group) => group.items.length > 0);
  const choose = postType === 'feature';
  const [kind, position] = focus.split(':');
  const picked = kind === 'features' ? readme?.features?.[Number(position)] : null;
  const cautions = picked
    ? [
        picked.maturity === 'planned' || picked.maturity === 'experimental'
          ? `The documents call this ${picked.maturity}.`
          : '',
        picked.claims.length > 0
          ? `Repeat with care: ${picked.claims.map((/** @type {any} */ c) => c.text).join('; ')}.`
          : '',
      ].filter(Boolean)
    : [];
  return (
    <>
      <p className="hint">Choose what the post will focus on. You can change this later.</p>
      <div role="radiogroup" aria-label="Post type" className="choices">
        {POST_TYPES.map((option) => (
          <label key={option.value} className="choice">
            <input
              type="radio"
              name="post-type"
              value={option.value}
              checked={postType === option.value}
              onChange={() => onChange(option.value)}
            />
            <span className="choice-title">{option.label}</span>
            <span className="choice-hint">{option.hint}</span>
          </label>
        ))}
      </div>
      {choose ? (
        groups.length === 0 ? (
          <p className="hint">
            Nothing was found to focus on. Go back to Analyze and press Refresh with AI to list
            features and use cases.
          </p>
        ) : (
          <Select label="Focus on" value={focus} onChange={onFocus}>
            <option value="">Choose a feature, use case or capability</option>
            {groups.map((group) => (
              <optgroup key={group.key} label={group.label}>
                {group.items.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.text}
                  </option>
                ))}
              </optgroup>
            ))}
          </Select>
        )
      ) : null}
      {cautions.map((line) => (
        <p key={line} className="hint">
          {line}
        </p>
      ))}
    </>
  );
}
