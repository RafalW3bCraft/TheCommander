import type { ReactNode } from "react";

// Deliberately small Markdown subset. Unrecognized syntax stays literal text.
// React escapes every text node: no HTML, image loading, or HTML injection sink.
function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const tokens = /(!?\[[^\]\n]+\]\([^\s)]+\)|`[^`\n]+`|\*\*[^*\n]+\*\*)/g;
  let start = 0;
  for (const match of text.matchAll(tokens)) {
    const index = match.index!;
    parts.push(text.slice(start, index));
    const token = match[0];
    if (token.startsWith("`")) {
      parts.push(<code key={index}>{token.slice(1, -1)}</code>);
    } else if (token.startsWith("**")) {
      parts.push(<strong key={index}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("!")) {
      // Keep images as text; even a harmless image URL can leak reader metadata.
      parts.push(token);
    } else {
      const split = token.indexOf("](");
      const label = token.slice(1, split);
      const href = token.slice(split + 2, -1);
      let safe = false;
      try {
        const url = new URL(href);
        safe =
          ["https:", "http:"].includes(url.protocol) &&
          !url.username &&
          !url.password;
      } catch {
        /* malformed and relative URLs remain literal */
      }
      parts.push(
        safe ? (
          <a key={index} href={href} target="_blank" rel="noopener noreferrer">
            {label}
          </a>
        ) : (
          token
        ),
      );
    }
    start = index + token.length;
  }
  parts.push(text.slice(start));
  return parts;
}

export function SafeMarkdown({
  text,
  className = "",
  headingLevel = 3,
}: {
  text: string;
  className?: string;
  headingLevel?: 3 | 4;
}) {
  const Heading = headingLevel === 4 ? "h4" : "h3";
  const lines = text.replaceAll("\r\n", "\n").split("\n");
  const blocks: ReactNode[] = [];
  for (let i = 0; i < lines.length;) {
    const line = lines[i];
    if (!line.trim()) {
      i++;
      continue;
    }
    const key = i;
    if (/^```/.test(line)) {
      const code: string[] = [];
      i++;
      while (i < lines.length && !/^```\s*$/.test(lines[i]))
        code.push(lines[i++]);
      if (i < lines.length) i++;
      blocks.push(
        <pre key={key}>
          <code>{code.join("\n")}</code>
        </pre>,
      );
    } else if (/^#{1,6} /.test(line)) {
      // Result headings are subordinate to the surrounding run/conversation.
      blocks.push(
        <Heading key={key}>{inline(line.replace(/^#{1,6} /, ""))}</Heading>,
      );
      i++;
    } else if (/^[-*] /.test(line) || /^\d+\. /.test(line)) {
      const ordered = /^\d+\. /.test(line);
      const pattern = ordered ? /^\d+\. / : /^[-*] /;
      const items: ReactNode[] = [];
      while (i < lines.length && pattern.test(lines[i])) {
        items.push(<li key={i}>{inline(lines[i].replace(pattern, ""))}</li>);
        i++;
      }
      blocks.push(
        ordered ? <ol key={key}>{items}</ol> : <ul key={key}>{items}</ul>,
      );
    } else {
      const paragraph: string[] = [line];
      i++;
      while (
        i < lines.length &&
        lines[i].trim() &&
        !/^(?:```|#{1,6} |[-*] |\d+\. )/.test(lines[i])
      )
        paragraph.push(lines[i++]);
      blocks.push(<p key={key}>{inline(paragraph.join("\n"))}</p>);
    }
  }
  return <div className={`markdown ${className}`}>{blocks}</div>;
}
