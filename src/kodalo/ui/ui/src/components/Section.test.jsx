import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Section from './Section.jsx';

describe('Section', () => {
  it('is closed until the title is clicked', async () => {
    const { container } = render(
      <Section title="Features" icon="bi-stars">
        <p>Body text</p>
      </Section>,
    );
    const details = /** @type {HTMLDetailsElement} */ (container.querySelector('details'));
    expect(details.open).toBe(false);
    await userEvent.click(screen.getByText('Features'));
    expect(details.open).toBe(true);
    expect(screen.getByText('Body text')).toBeVisible();
  });

  it('shows the count as a tag, including zero', () => {
    const { rerender } = render(
      <Section title="Features" icon="bi-stars" count={3}>
        <p>Body</p>
      </Section>,
    );
    expect(screen.getByText('3')).toHaveClass('topic');
    rerender(
      <Section title="Features" icon="bi-stars" count={0}>
        <p>Body</p>
      </Section>,
    );
    expect(screen.getByText('0')).toHaveClass('topic');
    rerender(
      <Section title="Features" icon="bi-stars">
        <p>Body</p>
      </Section>,
    );
    expect(document.querySelector('.topic')).toBeNull();
  });

  it('has no accessibility violations', async () => {
    const { container } = render(
      <Section title="Features" icon="bi-stars" count={2}>
        <p>Body</p>
      </Section>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
