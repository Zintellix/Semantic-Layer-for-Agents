import { Fragment } from "react";

// Highlight [ws1:CosmeticsVariant:220] object-ID citations inline.
const CITE = /\[(ws1:[A-Za-z]+:[^\]]+)\]/g;

export function AnswerView({ answer }: { answer: string }) {
  return (
    <div className="answer">
      {answer.split("\n").map((line, i) => (
        <p key={i} className="answer-line">
          {renderLine(line)}
        </p>
      ))}
    </div>
  );
}

function renderLine(line: string) {
  const out: (string | JSX.Element)[] = [];
  let last = 0;
  let m: RegExpExecArray | null;
  CITE.lastIndex = 0;
  while ((m = CITE.exec(line)) !== null) {
    if (m.index > last) out.push(line.slice(last, m.index));
    out.push(
      <span key={m.index} className="cite" title={m[1]}>
        {m[1]}
      </span>
    );
    last = m.index + m[0].length;
  }
  if (last < line.length) out.push(line.slice(last));
  return out.map((x, i) => <Fragment key={i}>{x}</Fragment>);
}
