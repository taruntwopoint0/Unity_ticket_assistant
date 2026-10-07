import { useEffect, useState } from 'react';
import Icon from '../icons.jsx';
import { api, isClosed } from '../api.js';

// Stand-in for the Unity portal home page so the widget can be demoed in context.
// In production only <ChatWidget> is embedded into the real portal.
const TILE_TONES = ['tone-a', 'tone-b', 'tone-c', 'tone-d', 'tone-e', 'tone-f'];

function StateBadge({ state }) {
  const tone = isClosed(state) ? 'done' : state === 'Awaiting approval' || state === 'Pending user' ? 'wait' : 'active';
  return <span className={`state is-${tone}`}><span className="dot" />{state}</span>;
}

// A category page: every offering with what it needs, its KB articles and the user's tickets on it.
function CategoryView({ category, tone, onBack, onAsk, onRaise }) {
  const [data, setData] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setData(null);
    setFailed(false);
    api.category(category.id).then(setData).catch(() => setFailed(true));
  }, [category.id]);

  return (
    <section className="category-view">
      <button type="button" className="back-link" onClick={onBack}><span className="flip"><Icon name="arrow" size={14} /></span>All categories</button>
      <div className={`category-banner ${tone}`}>
        <span className="tile-count">{category.count} offerings</span>
        <h2>{category.name}</h2>
        <p>{category.description}</p>
      </div>

      {failed && <p className="muted">Couldn't load this category. Please try again.</p>}
      {!data && !failed && <p className="muted">Loading offerings…</p>}

      <div className="offering-list">
        {data?.offerings.map((o) => (
          <article key={o.id} className="offering">
            <div className="offering-top">
              <span className={`offering-badge is-${o.type.toLowerCase()}`}>{o.type} Offering</span>
              <span className="offering-kind">{o.type === 'Support' ? 'Declare an issue → INC' : 'Request something → REQ'}</span>
            </div>
            <h3>{o.name}</h3>
            <p className="offering-desc">{o.use_when || o.description}</p>

            <dl className="routing">
              {o.support_group && <div><dt>Support group</dt><dd>{o.support_group}</dd></div>}
              {o.support_hours && <div><dt>Hours</dt><dd>{o.support_hours}</dd></div>}
              <div className="routing-wide"><dt>Raise in</dt><dd>{o.raise_path}</dd></div>
            </dl>

            <div className="offering-section">
              <span className="eyebrow">You'll be asked for</span>
              <ul className="needs">{o.fields.map((f) => <li key={f}><Icon name="check" size={13} />{f}</li>)}</ul>
            </div>

            {o.articles.length > 0 && (
              <div className="offering-section">
                <span className="eyebrow">Try first</span>
                {o.articles.map((a) => (
                  <button key={a.id} type="button" className="kb-link" onClick={() => onAsk(`kb:${a.id}`, a.title)}>
                    <Icon name="book" size={13} />{a.title}
                  </button>
                ))}
              </div>
            )}

            <div className="offering-section">
              <span className="eyebrow">Your tickets</span>
              {o.tickets.length === 0 && <p className="muted small">No tickets on this offering yet.</p>}
              {o.tickets.map((t) => (
                <button key={t.number} type="button" className="mini-ticket" onClick={() => onAsk(t.number)}>
                  <span className="mini-ticket-top"><span className="mono">{t.number}</span><StateBadge state={t.state} /></span>
                  <span className="mini-ticket-title">{t.short}</span>
                </button>
              ))}
            </div>

            <div className="offering-actions">
              <button type="button" className="btn btn-primary" onClick={() => onRaise(o)}>Raise this ticket</button>
              <a className="btn btn-outline" href={o.url} target="_blank" rel="noreferrer">Open in Unity<Icon name="external" size={13} /></a>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export default function Portal({ meta, categories, tickets, onAsk, onRaise }) {
  const [q, setQ] = useState('');
  const [openCat, setOpenCat] = useState(null);
  const submit = (e) => {
    e.preventDefault();
    if (q.trim()) { onAsk(q.trim()); setQ(''); }
  };
  const catIndex = categories.findIndex((c) => c.id === openCat);

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
          {catIndex >= 0 ? (
            <CategoryView category={categories[catIndex]} tone={TILE_TONES[catIndex % TILE_TONES.length]}
              onBack={() => setOpenCat(null)} onAsk={onAsk} onRaise={onRaise} />
          ) : (
            <>
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
                  <button key={c.id} type="button" onClick={() => { setOpenCat(c.id); window.scrollTo(0, 0); }}
                    className={`tile ${TILE_TONES[i % TILE_TONES.length]}`}>
                    <span className="tile-count">{c.count} offerings</span>
                    <span className="tile-name">{c.name}</span>
                    <span className="tile-desc">{c.description}</span>
                  </button>
                ))}
              </div>
            </>
          )}
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
