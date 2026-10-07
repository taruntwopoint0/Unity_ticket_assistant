import { useCallback, useEffect, useRef, useState } from 'react';
import Icon from '../icons.jsx';
import { api, formatDate, isClosed } from '../api.js';

const MAIN_MENU = [
  { label: 'Raise a new ticket', value: 'menu:raise' },
  { label: "Something isn't working (incident)", value: 'menu:issue' },
  { label: 'I need something (request)', value: 'menu:request' },
  { label: 'Access / user creation', value: 'menu:access' },
  { label: 'How do I…?', value: 'menu:howto' },
  { label: 'Browse offerings by category', value: 'menu:categories' },
  { label: 'My tickets', value: 'my tickets' },
];

// Minimal formatter for replies: **bold**, *italic*, "- " bullets and "1. " numbered lines.
function RichText({ text }) {
  const inline = (s) => s.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, i) => {
    if (part.startsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('*') && part.length > 2) return <em key={i}>{part.slice(1, -1)}</em>;
    return part;
  });
  const out = [];
  let list = null;
  let kind = null;
  text.split('\n').forEach((line, i) => {
    const bullet = line.match(/^\s*(?:- |\d+\. )/);
    if (bullet) {
      const k = bullet[0].trim() === '-' ? 'ul' : 'ol';
      if (!list || kind !== k) {
        list = [];
        kind = k;
        out.push(k === 'ul' ? <ul key={`l${i}`}>{list}</ul> : <ol key={`l${i}`}>{list}</ol>);
      }
      list.push(<li key={i}>{inline(line.slice(bullet[0].length))}</li>);
    } else {
      list = null;
      if (line.trim()) out.push(<p key={i}>{inline(line)}</p>);
    }
  });
  return out;
}

// A knowledge document referenced by a reply; opens in the document viewer.
function DocLink({ article, onOpen }) {
  return (
    <button type="button" className="card doc-link" onClick={() => onOpen(article)}>
      <span className="card-icon"><Icon name="book" size={16} /></span>
      <span className="article-title">
        <span className="eyebrow">Knowledge document · {article.id}</span>
        <span>{article.title}</span>
      </span>
      <span className="doc-open">Open<Icon name="arrow" size={13} /></span>
    </button>
  );
}

function DocViewer({ article, onClose }) {
  return (
    <div className="doc-view" role="document" aria-label={article.title}>
      <div className="doc-bar">
        <button type="button" className="back-link" onClick={onClose}><span className="flip"><Icon name="arrow" size={14} /></span>Back to chat</button>
      </div>
      <div className="doc-page">
        <span className="eyebrow">Knowledge document · {article.id}</span>
        <h2>{article.title}</h2>
        <p className="doc-summary">{article.summary}</p>
        <h4>Steps</h4>
        <ol>{article.steps.map((s, i) => <li key={i}><RichText text={s} /></li>)}</ol>
        {article.tip && <p className="note">{article.tip}</p>}
        {article.link?.url && (
          <a className="btn btn-primary btn-block" href={article.link.url} target="_blank" rel="noreferrer">
            {article.link.label}<Icon name="external" size={13} />
          </a>
        )}
      </div>
    </div>
  );
}

function OfferingBadge({ type }) {
  return <span className={`offering-badge is-${type.toLowerCase()}`}>{type} Offering</span>;
}

function StateBadge({ state }) {
  const tone = isClosed(state) ? 'done' : state === 'Awaiting approval' || state === 'Pending user' ? 'wait' : 'active';
  return <span className={`state is-${tone}`}><span className="dot" />{state}</span>;
}

function OfferingCard({ reply, onOpenDoc }) {
  const s = reply.service;
  const doc = reply.articles?.[0];
  return (
    <div className="card">
      <div className="card-top">
        <span className="card-icon"><Icon name="ticket" size={18} /></span>
        <div className="card-head">
          <OfferingBadge type={s.type} />
          <h3>{s.name}</h3>
          <p>{s.use_when || s.description}</p>
        </div>
      </div>
      <dl className="routing">
        {s.support_group && <div><dt>Support group</dt><dd>{s.support_group}</dd></div>}
        {s.support_hours && <div><dt>Hours</dt><dd>{s.support_hours}</dd></div>}
        <div className="routing-wide"><dt>Raise in</dt><dd>{s.raise_path || s.category} · {s.type === 'Support' ? 'creates an INC' : 'creates a REQ'}</dd></div>
      </dl>
      {reply.notice && <p className="notice"><Icon name="shield" size={13} />{reply.notice}</p>}
      <div className="card-actions">
        <a className="btn btn-primary" href={s.url} target="_blank" rel="noreferrer">Open in Unity<Icon name="external" size={13} /></a>
        {doc && <button type="button" className="btn btn-outline" onClick={() => onOpenDoc(doc)}>View steps</button>}
      </div>
    </div>
  );
}

function Pills({ options, onPick, disabled }) {
  return (
    <div className="pills">
      {options.map((o) => (
        <button key={o.value} type="button" className="pill" disabled={disabled} onClick={() => onPick(o.value, o.label)}>
          {o.meta && <span className={`pill-dot ${/^Support/.test(o.meta) ? 'is-support' : /^Service/.test(o.meta) ? 'is-service' : ''}`} />}
          <span className="pill-text">
            <span className="pill-label">{o.label}</span>
            {o.meta && <span className="pill-meta">{o.meta}</span>}
          </span>
        </button>
      ))}
    </div>
  );
}

// Offerings grouped by category, with "raise this when…" and a Raise button.
function OfferingList({ reply, onRaise }) {
  return (
    <div className="card offer-list">
      {reply.groups.map((g) => (
        <div key={g.category} className="offer-group">
          <span className="eyebrow">{g.category}</span>
          {g.offerings.map((o) => (
            <div key={o.id} className="offer-row">
              <span className={`pill-dot is-${o.type.toLowerCase()}`} />
              <div className="offer-text">
                <span className="offer-name">{o.name}</span>
                <span className="offer-when">{o.use_when}</span>
                {o.support_group && <span className="offer-group-name"><Icon name="users" size={12} />{o.support_group}</span>}
              </div>
              <button type="button" className="btn btn-outline btn-sm" onClick={() => onRaise(o)}>Raise</button>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

function BotMessage({ reply, onPick, latest, onRaise, onOpenDoc }) {
  return (
    <div className="row row-bot">
      <span className="bot-avatar" aria-hidden="true"><Icon name="sparkle" size={14} /></span>
      <div className="bot-col">
        <div className="bubble bubble-bot"><RichText text={reply.text} /></div>
        {reply.type === 'recommendation' && <OfferingCard reply={reply} onOpenDoc={onOpenDoc} />}
        {reply.type === 'offerings' && <OfferingList reply={reply} onRaise={onRaise} />}
        {reply.articles?.map((a) => <DocLink key={a.id} article={a} onOpen={onOpenDoc} />)}
        {reply.type === 'recommendation' && reply.alternatives?.length > 0 && (
          <>
            <span className="eyebrow eyebrow-pad">Not quite? Also consider</span>
            <Pills options={reply.alternatives.map((a) => ({ label: a.name, value: `service:${a.id}`, meta: `${a.type} Offering · ${a.category}` }))} onPick={onPick} disabled={!latest} />
          </>
        )}
        {reply.type === 'ticket' && (
          <div className="card">
            <div className="ticket-top"><span className="mono">{reply.ticket.number}</span><StateBadge state={reply.ticket.state} /></div>
            <h3 className="ticket-title">{reply.ticket.short}</h3>
            <dl className="facts">
              <div><dt>Assigned to</dt><dd>{reply.ticket.assigned_to}</dd></div>
              <div><dt>Last update</dt><dd>{formatDate(reply.ticket.updated)}</dd></div>
            </dl>
            <p className="note">{reply.ticket.last_note}</p>
            {reply.help && (
              <div className="next-step"><Icon name="info" size={14} /><span><strong>What happens next: </strong>{reply.help}</span></div>
            )}
            <a className="btn btn-outline btn-block" href={reply.ticket.url} target="_blank" rel="noreferrer">View in Unity<Icon name="external" size={13} /></a>
          </div>
        )}
        {reply.type === 'tickets' && (
          <div className="ticket-list">
            {reply.tickets.map((t) => (
              <button key={t.number} type="button" className="ticket-row" onClick={() => onPick(t.number)}>
                <span className="ticket-row-top"><span className="mono">{t.number}</span><StateBadge state={t.state} /></span>
                <span className="ticket-row-title">{t.short}</span>
              </button>
            ))}
          </div>
        )}
        {reply.options && reply.options_label && <span className="eyebrow eyebrow-pad">{reply.options_label}</span>}
        {reply.options && <Pills options={reply.options} onPick={onPick} disabled={!latest} />}
        {reply.link && (
          <a className="text-link" href={reply.link.url} target="_blank" rel="noreferrer">{reply.link.label}<Icon name="external" size={12} /></a>
        )}
      </div>
    </div>
  );
}

export default function ChatWidget({ meta, open, onOpenChange, seed }) {
  const [messages, setMessages] = useState([]);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState('');
  const [expanded, setExpanded] = useState(false);
  const [doc, setDoc] = useState(null); // knowledge document open in the viewer
  const lastQuery = useRef(null);
  const history = useRef([]);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  const firstName = meta?.user?.name?.split(' ').slice(-1)[0];
  const welcome = {
    type: 'text',
    text: `Hi${firstName ? ` ${firstName}` : ''}, I'm the **Unity Assistant**. Tell me what you need and I'll show you the right ticket to raise, with the knowledge document that explains the steps.\nChoose an option below or type your question.`,
    options: MAIN_MENU,
  };

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages.length, busy]);
  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 150); }, [open]);

  const send = useCallback(async (value, display) => {
    const shown = display || value;
    const past = history.current.slice(-8);
    history.current = [...history.current, { role: 'user', text: shown }];
    setMessages((m) => [...m, { role: 'user', text: shown }]);
    setDoc(null);
    setBusy(true);
    try {
      const reply = await api.chat(value, lastQuery.current, past);
      if (reply.query) lastQuery.current = reply.query;
      else if (!/^(service|menu|category|kb):/.test(value)) lastQuery.current = value;
      history.current = [...history.current, { role: 'assistant', text: reply.text }];
      setMessages((m) => [...m, { role: 'bot', reply }]);
    } catch {
      setMessages((m) => [...m, { role: 'bot', reply: { type: 'text', text: "Sorry, I couldn't reach the service. Please try again in a moment.", options: MAIN_MENU.slice(0, 3) } }]);
    } finally {
      setBusy(false);
    }
  }, []);

  const raise = useCallback((o) => send(`service:${o.id}`, `Raise a ticket: ${o.name}`), [send]);

  // Questions and "Raise this ticket" clicks from the portal page are handed to the assistant.
  useEffect(() => { if (seed?.text) send(seed.text, seed.display); }, [seed, send]);

  const submit = (e) => {
    e.preventDefault();
    const v = text.trim();
    if (!v || busy) return;
    setText('');
    send(v);
  };

  const restart = () => { setMessages([]); history.current = []; lastQuery.current = null; setDoc(null); };
  const lastBot = messages.map((m) => m.role).lastIndexOf('bot');

  return (
    <>
      <div className={`widget ${open ? 'is-open' : ''} ${expanded ? 'is-expanded' : ''}`} role="dialog" aria-label="Unity Assistant" aria-hidden={!open}>
        <header className="widget-head">
          <div className="widget-brand">
            <span className="widget-mark" aria-hidden="true"><Icon name="sparkle" size={18} /></span>
            <div>
              <div className="widget-title">Unity Assistant</div>
            </div>
          </div>
          <div className="widget-tools">
            <button type="button" onClick={restart} aria-label="Start over" title="Start over"><Icon name="refresh" size={16} /></button>
            <button type="button" className="hide-sm" onClick={() => setExpanded(!expanded)} aria-label={expanded ? 'Shrink' : 'Expand'} title={expanded ? 'Shrink' : 'Expand'}>
              <Icon name={expanded ? 'shrink' : 'expand'} size={16} />
            </button>
            <button type="button" onClick={() => onOpenChange(false)} aria-label="Close" title="Close"><Icon name="close" size={18} /></button>
          </div>
        </header>

        <div className="widget-body">
          <div className="day-sep"><span>Today</span></div>
          <BotMessage reply={welcome} onPick={send} latest={messages.length === 0} onRaise={raise} onOpenDoc={setDoc} />
          {messages.map((m, i) => m.role === 'user' ? (
            <div key={i} className="row row-user"><div className="bubble bubble-user">{m.text}</div></div>
          ) : (
            <BotMessage key={i} reply={m.reply} onPick={send} latest={i === lastBot && !busy} onRaise={raise} onOpenDoc={setDoc} />
          ))}
          {busy && (
            <div className="row row-bot">
              <span className="bot-avatar" aria-hidden="true"><Icon name="sparkle" size={14} /></span>
              <div className="bubble bubble-bot typing" aria-label="Assistant is typing"><span /><span /><span /></div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form className="composer" onSubmit={submit}>
          <input ref={inputRef} value={text} onChange={(e) => setText(e.target.value)}
            placeholder="Write a message" aria-label="Message" maxLength={1000} />
          <button type="submit" className="send" disabled={!text.trim() || busy} aria-label="Send"><Icon name="send" size={16} /></button>
        </form>
        <p className="widget-foot">The assistant suggests offerings — you raise the ticket in Unity. Don't share personal data.</p>
        {doc && <DocViewer article={doc} onClose={() => setDoc(null)} />}
      </div>

      <button type="button" className={`launcher ${open ? 'is-open' : ''}`} onClick={() => onOpenChange(!open)}
        aria-label={open ? 'Close assistant' : 'Open Unity Assistant'}>
        <Icon name={open ? 'close' : 'chat'} size={24} />
      </button>
    </>
  );
}
