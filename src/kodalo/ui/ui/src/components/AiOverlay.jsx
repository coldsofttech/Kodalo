/**
 * A see-through screen over the whole window while work is in progress, with a small animation and
 * a moving progress bar. It blocks clicks until the work ends; screen readers hear the message. By
 * default it shows the robot of the AI; give another Bootstrap icon (for example for a plain
 * refresh) and a spinning icon is shown instead.
 * @param {{ message: string, icon?: string }} props
 */
export default function AiOverlay({ message, icon }) {
  return (
    <div className="ai-overlay" role="status" aria-live="polite">
      <div className="ai-overlay-card">
        <div className="ai-robot" aria-hidden="true">
          {icon ? (
            <i className={`bi ${icon} ai-robot-body ai-spin`} />
          ) : (
            <>
              <i className="bi bi-robot ai-robot-body" />
              <i className="bi bi-stars ai-spark ai-spark-1" />
              <i className="bi bi-stars ai-spark ai-spark-2" />
              <i className="bi bi-stars ai-spark ai-spark-3" />
            </>
          )}
        </div>
        <p>{message}</p>
        <div className="ai-progress" aria-hidden="true">
          <span />
        </div>
      </div>
    </div>
  );
}
