import { describe, expect, it, vi } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useState } from 'react';
import { UnsavedContext, useSavedValues, useUnsavedGuard } from './unsaved.js';

/** The ids that currently hold unsaved edits, as the app would collect them. */
function collector() {
  const dirty = new Set();
  const report = vi.fn((id, isDirty) => (isDirty ? dirty.add(id) : dirty.delete(id)));
  return { dirty, report };
}

function Field() {
  const [value, setValue] = useState('saved');
  const markSaved = useSavedValues({ value });
  return (
    <>
      <button type="button" onClick={() => markSaved({ value: 'saved' })}>
        Load
      </button>
      <button type="button" onClick={() => setValue('edited')}>
        Edit
      </button>
      <button type="button" onClick={() => markSaved({ value })}>
        Save
      </button>
    </>
  );
}

function Plain({ dirty }) {
  useUnsavedGuard(dirty);
  return <p>Page</p>;
}

describe('useUnsavedGuard', () => {
  it('reports while dirty and stops when the page goes away', () => {
    const { dirty, report } = collector();
    const { rerender, unmount } = render(
      <UnsavedContext.Provider value={report}>
        <Plain dirty={false} />
      </UnsavedContext.Provider>,
    );
    expect(dirty.size).toBe(0);

    rerender(
      <UnsavedContext.Provider value={report}>
        <Plain dirty />
      </UnsavedContext.Provider>,
    );
    expect(dirty.size).toBe(1);

    unmount();
    expect(dirty.size).toBe(0);
  });

  it('does nothing without an app around it', () => {
    render(<Plain dirty />);

    expect(screen.getByText('Page')).toBeInTheDocument();
  });
});

describe('useSavedValues', () => {
  it('is clean until loaded, dirty after an edit and clean again once saved', async () => {
    const { dirty, report } = collector();
    render(
      <UnsavedContext.Provider value={report}>
        <Field />
      </UnsavedContext.Provider>,
    );

    await userEvent.click(screen.getByText('Edit'));
    expect(dirty.size).toBe(0); // nothing was loaded yet, so there is nothing to compare with

    await act(async () => userEvent.click(screen.getByText('Load')));
    expect(dirty.size).toBe(1); // the form now differs from what was loaded

    await userEvent.click(screen.getByText('Save'));
    expect(dirty.size).toBe(0);
  });
});
