import { describe, expect, it, vi } from 'vitest';
import { act, renderHook, waitFor } from '@testing-library/react';
import { errorText, useCatalog } from './catalog.js';

describe('errorText', () => {
  it('uses the message of an error and the fallback for anything else', () => {
    expect(errorText(new Error('Nope'), 'Fallback')).toBe('Nope');
    expect(errorText('boom', 'Fallback')).toBe('Fallback');
  });
});

describe('useCatalog', () => {
  it('loads the list', async () => {
    const load = vi.fn().mockResolvedValue([{ id: 'a' }]);

    const { result } = renderHook(() => useCatalog(load, 'No list.', 0, undefined));

    expect(result.current.items).toBeNull();
    await waitFor(() => expect(result.current.items).toEqual([{ id: 'a' }]));
    expect(result.current.error).toBe('');
  });

  it('shows an empty list and why when it cannot be loaded', async () => {
    const load = vi.fn().mockRejectedValue('broken');

    const { result } = renderHook(() => useCatalog(load, 'No list.', 0, undefined));

    await waitFor(() => expect(result.current.items).toEqual([]));
    expect(result.current.error).toBe('No list.');
  });

  it('reloads when the revision changes', async () => {
    let list = [1];
    const load = vi.fn(async () => list);
    const { result, rerender } = renderHook(
      ({ revision }) => useCatalog(load, 'No.', revision, undefined),
      { initialProps: { revision: 0 } },
    );
    await waitFor(() => expect(result.current.items).toEqual([1]));

    list = [1, 2];
    rerender({ revision: 1 });

    await waitFor(() => expect(result.current.items).toEqual([1, 2]));
  });

  it('runs a change, reloads the list, says it is done and tells the app', async () => {
    let list = [1];
    const load = vi.fn(async () => list);
    const onChange = vi.fn();
    const task = vi.fn(async () => {
      list = [1, 2];
    });
    const { result } = renderHook(() => useCatalog(load, 'No.', 0, onChange));
    await waitFor(() => expect(result.current.items).toEqual([1]));

    /** @type {boolean | undefined} */
    let worked;
    await act(async () => {
      worked = await result.current.act(task, 'Added.');
    });

    expect(worked).toBe(true);
    expect(result.current.items).toEqual([1, 2]);
    expect(result.current.notice).toBe('Added.');
    expect(result.current.busy).toBe(false);
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it('shows why a change failed and keeps the list', async () => {
    const load = vi.fn().mockResolvedValue([1]);
    const onChange = vi.fn();
    const { result } = renderHook(() => useCatalog(load, 'No.', 0, onChange));
    await waitFor(() => expect(result.current.items).toEqual([1]));

    /** @type {boolean | undefined} */
    let worked;
    await act(async () => {
      worked = await result.current.act(() => Promise.reject(new Error('Name taken.')), 'Done.');
    });

    expect(worked).toBe(false);
    expect(result.current.error).toBe('Name taken.');
    expect(result.current.notice).toBe('');
    expect(result.current.items).toEqual([1]);
    expect(onChange).not.toHaveBeenCalled();
  });
});
