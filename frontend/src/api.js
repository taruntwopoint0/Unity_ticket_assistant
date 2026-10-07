async function call(path, options) {
  const res = await fetch(`/api${path}`, options);
  if (!res.ok) throw new Error(`${path} failed (${res.status})`);
  return res.json();
}

export const api = {
  meta: () => call('/meta'),
  categories: () => call('/categories'),
  category: (id) => call(`/categories/${encodeURIComponent(id)}`),
  tickets: () => call('/tickets'),
  chat: (message, lastQuery, history) =>
    call('/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, last_query: lastQuery || null, history }),
    }),
};

export function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
}

export const isClosed = (state) => ['Resolved', 'Closed', 'Cancelled'].includes(state);
