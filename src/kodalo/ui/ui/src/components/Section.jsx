/**
 * A collapsible block, closed until opened. The count, when given, shows as a tag in the header.
 * @param {{ title: string, icon: string, count?: number, children: import('react').ReactNode }} props
 */
export default function Section({ title, icon, count, children }) {
  return (
    <details className="accordion">
      <summary>
        <i className="bi bi-chevron-right accordion-chevron" aria-hidden="true" />
        <i className={`bi ${icon}`} aria-hidden="true" />
        <span className="accordion-title">{title}</span>
        {count === undefined ? null : <span className="topic">{count}</span>}
      </summary>
      <div className="accordion-body">{children}</div>
    </details>
  );
}
