import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Button, ComboBox, NumberField, Select, Switch, TextArea, TextField } from './controls.jsx';
import { setChecked, typeInto } from '../testing.js';

describe('TextField', () => {
  it('reports what is typed and shows its hint', () => {
    const onChange = vi.fn();
    render(<TextField label="Name" value="Ada" hint="Shown to everyone" onChange={onChange} />);
    const field = screen.getByLabelText('Name');
    expect(field).toHaveProperty('value', 'Ada');
    expect(screen.getByText('Shown to everyone')).toBeInTheDocument();
    typeInto(field, 'Grace');
    expect(onChange).toHaveBeenCalledWith('Grace');
  });

  it('marks an invalid value, and hides a label that is only for assistive technology', () => {
    render(
      <TextField label="Hex" value="#zz" invalid hideLabel maxLength={7} onChange={vi.fn()} />,
    );
    const field = screen.getByLabelText('Hex');
    expect(field).toHaveAttribute('aria-invalid', 'true');
    expect(field).toHaveAttribute('maxlength', '7');
    expect(field).toBeEmptyDOMElement();
  });

  it('turns off autocomplete for a password', () => {
    render(<TextField label="Key" value="" type="password" onChange={vi.fn()} />);
    expect(screen.getByLabelText('Key')).toHaveAttribute('autocomplete', 'off');
  });
});

describe('TextArea', () => {
  it('reports what is typed', () => {
    const onChange = vi.fn();
    render(<TextArea label="Notes" value="" rows={5} onChange={onChange} />);
    const area = screen.getByLabelText('Notes');
    expect(area).toHaveAttribute('rows', '5');
    typeInto(area, 'Hello');
    expect(onChange).toHaveBeenCalledWith('Hello');
  });
});

describe('NumberField', () => {
  it('keeps the number between its limits and ignores text', () => {
    const onChange = vi.fn();
    render(<NumberField label="Size" value={10} min={5} max={60} onChange={onChange} />);
    const field = screen.getByLabelText('Size');
    expect(field).toHaveProperty('value', '10');
    typeInto(field, '99');
    typeInto(field, '1');
    typeInto(field, '42');
    typeInto(field, 'abc');
    expect(onChange.mock.calls).toEqual([[60], [5], [42]]);
  });
});

describe('Switch', () => {
  it('reports the new state', () => {
    const onChange = vi.fn();
    render(<Switch label="Enabled" checked={false} onChange={onChange} />);
    setChecked(screen.getByLabelText('Enabled'), true);
    expect(onChange).toHaveBeenCalledWith(true);
  });
});

describe('Button', () => {
  it('runs its action when clicked', async () => {
    const onClick = vi.fn();
    render(<Button onClick={onClick}>Save</Button>);
    await userEvent.click(screen.getByText('Save'));
    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('does nothing while disabled', async () => {
    const onClick = vi.fn();
    render(
      <Button disabled onClick={onClick}>
        Save
      </Button>,
    );
    await userEvent.click(screen.getByText('Save'));
    expect(onClick).not.toHaveBeenCalled();
    expect(screen.getByText('Save')).toHaveAttribute('disabled');
  });

  it('gives an icon-only button its name and tooltip, and flags a dangerous one', () => {
    render(
      <Button label="Remove logo" title="Remove logo" danger>
        <i className="bi bi-trash" aria-hidden="true" />
      </Button>,
    );
    const button = screen.getByLabelText('Remove logo');
    expect(button).toHaveAttribute('title', 'Remove logo');
    expect(button).toHaveAttribute('danger');
  });
});

describe('Select', () => {
  it('reports the chosen option', async () => {
    const onChange = vi.fn();
    render(
      <Select label="Font" value="a" onChange={onChange}>
        <option value="a">A</option>
        <option value="b">B</option>
      </Select>,
    );
    expect(screen.getByLabelText('Font')).toHaveValue('a');
    await userEvent.selectOptions(screen.getByLabelText('Font'), 'b');
    expect(onChange).toHaveBeenCalledWith('b');
  });
});

describe('ComboBox', () => {
  it('suggests options but accepts any text', async () => {
    const onChange = vi.fn();
    const { container } = render(
      <ComboBox
        label="Model"
        value=""
        options={['one', 'two']}
        maxLength={20}
        onChange={onChange}
      />,
    );
    const input = screen.getByLabelText('Model');
    expect(input).toHaveAttribute('list', container.querySelector('datalist')?.id);
    expect(
      [...container.querySelectorAll('option')].map((option) => option.getAttribute('value')),
    ).toEqual(['one', 'two']);
    await userEvent.type(input, 'x');
    expect(onChange).toHaveBeenCalledWith('x');
  });
});

describe('controls together', () => {
  it('have no accessibility violations', async () => {
    const { container } = render(
      <form>
        <TextField label="Name" value="" onChange={vi.fn()} />
        <TextArea label="Notes" value="" onChange={vi.fn()} />
        <NumberField label="Size" value={10} min={5} max={60} onChange={vi.fn()} />
        <Switch label="Enabled" checked onChange={vi.fn()} />
        <Select label="Font" value="a" onChange={vi.fn()}>
          <option value="a">A</option>
        </Select>
        <ComboBox label="Model" value="" options={['one']} onChange={vi.fn()} />
        <Button>Save</Button>
      </form>,
    );
    expect(await axe(container)).toHaveNoViolations();
  });
});
