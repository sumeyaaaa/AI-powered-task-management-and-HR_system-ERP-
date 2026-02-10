import React, { useMemo } from 'react';

interface SimpleMarkdownTextProps {
  text: string;
  className?: string;
}

export const SimpleMarkdownText: React.FC<SimpleMarkdownTextProps> = ({
  text,
  className = '',
}) => {
  const html = useMemo(() => {
    if (!text) return '';
    let safe = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');

    // Bold and italic
    safe = safe.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    safe = safe.replace(/\*(.+?)\*/g, '<em>$1</em>');

    const lines = safe.split('\n');
    const processed: string[] = [];
    let inList = false;

    for (const line of lines) {
      const trimmed = line.trim();
      const bulletMatch = /^-\s+(.+)$/.exec(trimmed);
      const numMatch = /^[0-9]+\.\s+(.+)$/.exec(trimmed);

      if (bulletMatch || numMatch) {
        if (!inList) {
          processed.push('<ul class="md-list">');
          inList = true;
        }
        processed.push(`<li>${(bulletMatch || numMatch)![1]}</li>`);
      } else {
        if (inList) {
          processed.push('</ul>');
          inList = false;
        }
        if (trimmed.length === 0) {
          processed.push('<br />');
        } else {
          processed.push(`<p>${line}</p>`);
        }
      }
    }
    if (inList) {
      processed.push('</ul>');
    }
    return processed.join('');
  }, [text]);

  if (!text) {
    return null;
  }

  return (
    <span
      className={className}
      dangerouslySetInnerHTML={{ __html: html }}
    />
  );
};

export default SimpleMarkdownText;




