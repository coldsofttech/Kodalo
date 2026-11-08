import { describe, expect, it } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import AiOverlay from './AiOverlay.jsx';

describe('AiOverlay', () => {
  it('tells screen readers what the AI is doing', async () => {
    const { container } = render(<AiOverlay message="The AI is choosing colors…" />);
    expect(screen.getByRole('status')).toHaveTextContent('The AI is choosing colors…');
    expect(await axe(container)).toHaveNoViolations();
  });
});
