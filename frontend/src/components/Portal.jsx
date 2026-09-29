import { useState } from 'react';
import Icon from '../icons.jsx';

// Stand-in for the Unity portal home page so the widget can be demoed in context.
// In production only <ChatWidget> is embedded into the real portal.
const TILE_TONES = ['tone-a', 'tone-b', 'tone-c', 'tone-d', 'tone-e', 'tone-f'];

export default function Portal({ meta, categories, tickets, onAsk }) {
  const [q, setQ] = useState('');
  const submit = (e) => {
    e.preventDefault();
    if (q.trim()) { onAsk(q.trim()); setQ(''); }
  };

  return (
    <div className="portal">
      <header className="portal-head">
        <div className="portal-brand">
          <span>Service Portal - UNITY</span>
        </div>
        {meta && <span className="portal-user"><span className="avatar">{meta.user.initials}</span>{meta.user.name}</span>}
      </header>

      <div className="portal-grid">
        <main className="portal-main">
          <section className="hero">
            <h1>How can we help you today?</h1>
            <p>Describe your issue or request and the Unity Assistant will find the right offering.</p>
            <form className="hero-search" onSubmit={submit}>
              <Icon name="sparkle" size={18} />
              <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="e.g. Eloqua campaign won't publish, or I need a DocuSign account" aria-label="Ask the Unity Assistant" />
              <button type="submit" className="btn btn-primary">Ask assistant</button>
            </form>
          </section>

          <h2 className="section-title">Categories</h2>
          <div className="tiles">
            {categories.map((c, i) => (
              <a key={c.id} href={c.url} target="_blank" rel="noreferrer" className={`tile ${TILE_TONES[i % TILE_TONES.length]}`}>
                <span className="tile-count">{c.count} offerings</span>
                <span className="tile-name">{c.name}</span>
                <span className="tile-desc">{c.description}</span>
              </a>
            ))}
          </div>
        </main>

        <aside className="portal-side">
          <div className="side-block">
            <h3>My recent tickets</h3>
            {tickets.map((t) => (
              <button key={t.number} type="button" className="side-row" onClick={() => onAsk(t.number)}>
                <span className="side-title">{t.short}</span>
                <span className="side-meta">{t.number} · {t.state}</span>
              </button>
            ))}
          </div>
          <div className="side-block side-cta">
            <h3>Not sure which offering?</h3>
            <p>With 160+ offerings, the assistant can point you to the right one in a few seconds.</p>
            <button type="button" className="btn btn-outline" onClick={() => onAsk(null)}>Open assistant</button>
          </div>
        </aside>
      </div>
    </div>
  );
}
