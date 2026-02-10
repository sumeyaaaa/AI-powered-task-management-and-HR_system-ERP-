import React, { useMemo, useRef } from 'react';

interface RichTextNoteEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}

export const RichTextNoteEditor: React.FC<RichTextNoteEditorProps> = ({
  value,
  onChange,
  placeholder,
}) => {
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const updateValue = (next: string, cursorOffset?: number) => {
    onChange(next);
    if (textareaRef.current) {
      const el = textareaRef.current;
      const pos = typeof cursorOffset === 'number' ? cursorOffset : next.length;
      requestAnimationFrame(() => {
        el.focus();
        el.selectionStart = el.selectionEnd = pos;
      });
    }
  };

  const wrapSelection = (before: string, after: string = before) => {
    const el = textareaRef.current;
    if (!el) {
      updateValue(`${before}${value}${after}`);
      return;
    }
    const start = el.selectionStart ?? 0;
    const end = el.selectionEnd ?? 0;
    const selected = value.slice(start, end) || 'text';
    const next =
      value.slice(0, start) + before + selected + after + value.slice(end);
    const newCursor = start + before.length + selected.length + after.length;
    updateValue(next, newCursor);
  };

  const addLinePrefix = (prefix: string) => {
    const el = textareaRef.current;
    if (!el) {
      updateValue(`${prefix} ${value}`);
      return;
    }
    const start = el.selectionStart ?? 0;
    const lineStart = value.lastIndexOf('\n', start - 1) + 1;
    const next =
      value.slice(0, lineStart) + prefix + ' ' + value.slice(lineStart);
    const newCursor = start + prefix.length + 1;
    updateValue(next, newCursor);
  };

  const clearContent = () => {
    updateValue('');
  };

  const renderedHtml = useMemo(() => {
    let html = value || '';
    html = html
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/\*(.+?)\*/g, '<em>$1</em>');
    const lines = html.split('\n');
    const listLines = lines.map((line) => {
      if (line.trim().startsWith('- ')) {
        return `<li>${line.trim().slice(2)}</li>`;
      }
      if (line.trim().match(/^[0-9]+\.\s+/)) {
        return `<li>${line.trim().replace(/^[0-9]+\.\s+/, '')}</li>`;
      }
      if (!line.trim()) {
        return '<br />';
      }
      return `<p>${line}</p>`;
    });
    const joined = listLines.join('');
    const ulWrapped = joined.replace(
      /(<li>[\s\S]*?<\/li>)/g,
      '<ul class="rich-note-list">$1</ul>'
    );
    return ulWrapped;
  }, [value]);

  return (
    <div className="rich-note-editor">
      <div className="rich-note-toolbar">
        <button
          type="button"
          className="rich-note-btn"
          onClick={() => wrapSelection('**')}
        >
          <strong>B</strong>
        </button>
        <button
          type="button"
          className="rich-note-btn"
          onClick={() => wrapSelection('*')}
        >
          <em>I</em>
        </button>
        <button
          type="button"
          className="rich-note-btn"
          onClick={() => addLinePrefix('-')}
        >
          • Bullet
        </button>
        <button
          type="button"
          className="rich-note-btn"
          onClick={() => addLinePrefix('1.')}
        >
          1.
        </button>
        <button
          type="button"
          className="rich-note-btn secondary"
          onClick={clearContent}
        >
          Clear
        </button>
      </div>
      <textarea
        ref={textareaRef}
        className="rich-note-textarea"
        placeholder={placeholder}
        rows={6}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
      <div className="rich-note-preview">
        <div
          className="rich-note-preview-body"
          dangerouslySetInnerHTML={{ __html: renderedHtml || '<p class="placeholder">Preview appears here…</p>' }}
        />
      </div>
      <p className="rich-note-hint">Preview shows how your notes will look with bold, italic, and bullets.</p>
    </div>
  );
};

export default RichTextNoteEditor;


