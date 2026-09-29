import { useCallback, useEffect, useRef, useState } from 'react';
import Icon from '../icons.jsx';
import { api, formatDate, isClosed } from '../api.js';

const MAIN_MENU = [
  { label: "Something isn't working", value: 'menu:issue' },
  { label: 'Access / user creation', value: 'menu:access' },
  { label: 'Browse offerings by category', value: 'menu:categories' },
  { label: 'My tickets', value: 'my tickets' },
  { label: 'Something else', value: 'menu:else' },
];

// Minimal formatter for replies: **bold**, *italic* and "- " bullet lines.
function RichText({ text }) {
  const inline = (s) => s.split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g).map((part, i) => {
    if (part.startsWith('**')) return <strong key={i}>{part.slice(2, -2)}</strong>;
    if (part.startsWith('*') && part.length > 2) return <em key={i}>{part.slice(1, -1)}</em>;
    return part;
  });
  const out = [];
  let list = null;
  text.split('\n').forEach((line, i) => {
    if (line.startsWith('- ')) {
      if (!list) { list = []; out.push(<ul key={`l${i}`}>{list}</ul>); }
      list.push(<li key={i}>{inline(line.slice(2))}</li>);
    } else {
      list = null;
      if (line.trim()) out.push(<p key={i}>{inline(line)}</p>);
    }
  });
  return out;
}

function OfferingBadge({ type }) {
  return <span className={`offering-badge is-${type.toLowerCase()}`}>{type} Offering</span>;
}

function StateBadge({ state }) {
  const tone = isClosed(state) ? 'done' : state === 'Awaiting approval' ? 'wait' : 'active';
  return <span className={`state is-${tone}`}><span className="dot" />{state}</span>;
}

function Draft({ service, draft, notify }) {
  const [summary, setSummary] = useState(draft.summary);
  const [details, setDetails] = useState(draft.description);
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(`${summary}\n\n${details}`);
      notify('Copied — paste it into the Unity form');
    } catch {
      notify('Copy is not available in this browser');
    }
  };
  return (
    <div className="draft">
      <div className="draft-ready">
        <span className="eyebrow">Keep ready</span>
        <ul>{service.fields.map((f) => <li key={f}><Icon name="check" size={13} />{f}</li>)}</ul>
      </div>
      <label className="field"><span>Title</span>
        <input value={summary} onChange={(e) => setSummary(e.target.value)} />
      </label>
      <label className="field"><span>Description</span>
        <textarea rows={6} value={details} onChange={(e) => setDetails(e.target.value)} />
      </label>
      <button type="button" className="btn btn-outline btn-block" onClick={copy}>
        <Icon name="copy" size={14} />Copy ticket text
      </button>
    </div>
  );
}

function OfferingCard({ reply, notify }) {
  const s = reply.service;
  const [open, setOpen] = useState(false);
  return (
    <div className="card">
      <div className="card-top">
        <span className="card-icon"><Icon name="briefcase" size={18} /></span>
        <div className="card-head">
          <OfferingBadge type={s.type} />
          <h3>{s.name}</h3>
          <p>{s.description}</p>
        </div>
      </div>
      <div className="card-meta">
        <span>{s.category}</span>
        {reply.reasons?.length > 0 && <span>Matched: {reply.reasons.slice(0, 3).join(', ')}</span>}
      </div>
      {reply.notice && <p className="notice"><Icon name="shield" size={13} />{reply.notice}</p>}
      <div className="card-actions">
        <a className="btn btn-primary" href={s.url} target="_blank" rel="noreferrer">Request<Icon name="external" size={13} /></a>
        <button type="button" className="btn btn-outline" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? 'Hide draft' : 'Prepare ticket'}
        </button>
      </div>
      {open && <Draft service={s} draft={reply.draft} notify={notify} />}
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

function BotMessage({ reply, onPick, notify, latest }) {
  return (
    <div className="row row-bot">
      <span className="bot-avatar" aria-hidden="true"><Icon name="sparkle" size={14} /></span>
      <div className="bot-col">
        <div className="bubble bubble-bot"><RichText text={reply.text} /></div>
        {reply.type === 'recommendation' && <OfferingCard reply={reply} notify={notify} />}
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
  const [toast, setToast] = useState('');
  const lastQuery = useRef(null);
  const history = useRef([]);
  const endRef = useRef(null);
  const inputRef = useRef(null);

  const firstName = meta?.user?.name?.split(' ').slice(-1)[0];
  const welcome = {
    type: 'text',
    text: `Hi${firstName ? ` ${firstName}` : ''}, I'm the **Unity Assistant**. I can help you find the right offering, prepare your ticket and check on existing requests.\nChoose an option below or type your question.`,
    options: MAIN_MENU,
  };

  const notify = useCallback((msg) => { setToast(msg); setTimeout(() => setToast(''), 2200); }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages.length, busy]);
  useEffect(() => { if (open) setTimeout(() => inputRef.current?.focus(), 150); }, [open]);

  const send = useCallback(async (value, display) => {
    const shown = display || value;
    const past = history.current.slice(-8);
    history.current = [...history.current, { role: 'user', text: shown }];
    setMessages((m) => [...m, { role: 'user', text: shown }]);
    setBusy(true);
    try {
      const reply = await api.chat(value, lastQuery.current, past);
      // Keep the user's own words so a later pick ("service:ID") drafts the ticket from them.
      if (reply.query) lastQuery.current = reply.query;
      else if (!/^(service|menu|category):/.test(value)) lastQuery.current = value;
      history.current = [...history.current, { role: 'assistant', text: reply.text }];
      setMessages((m) => [...m, { role: 'bot', reply }]);
    } catch {
      setMessages((m) => [...m, { role: 'bot', reply: { type: 'text', text: "Sorry, I couldn't reach the service. Please try again in a moment.", options: MAIN_MENU.slice(0, 3) } }]);
    } finally {
      setBusy(false);
    }
  }, []);

  // A question typed into the portal page's search box is handed to the assistant.
  useEffect(() => { if (seed?.text) send(seed.text); }, [seed, send]);

  const submit = (e) => {
    e.preventDefault();
    const v = text.trim();
    if (!v || busy) return;
    setText('');
    send(v);
  };

  const restart = () => { setMessages([]); history.current = []; lastQuery.current = null; };
  const lastBot = messages.map((m) => m.role).lastIndexOf('bot');

  return (
    <>
      <div className={`widget ${open ? 'is-open' : ''} ${expanded ? 'is-expanded' : ''}`} role="dialog" aria-label="Unity Assistant" aria-hidden={!open}>
        <header className="widget-head">
          <div className="widget-brand">
            <span className="widget-mark" aria-hidden="true"><Icon name="sparkle" size={18} /></span>
            <div>
              <div className="widget-title">Unity Assistant</div>
              <div className="widget-status">
                <span className="live-dot" />{meta?.ai ? `AI-powered · ${meta.ai}` : 'Online · guided mode'}
              </div>
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
          <BotMessage reply={welcome} onPick={send} notify={notify} latest={messages.length === 0} />
          {messages.map((m, i) => m.role === 'user' ? (
            <div key={i} className="row row-user"><div className="bubble bubble-user">{m.text}</div></div>
          ) : (
            <BotMessage key={i} reply={m.reply} onPick={send} notify={notify} latest={i === lastBot && !busy} />
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
        <div className={`toast ${toast ? 'is-shown' : ''}`} role="status">{toast}</div>
      </div>

      <button type="button" className={`launcher ${open ? 'is-open' : ''}`} onClick={() => onOpenChange(!open)}
        aria-label={open ? 'Close assistant' : 'Open Unity Assistant'}>
        <Icon name={open ? 'close' : 'chat'} size={24} />
      </button>
    </>
  );
}
