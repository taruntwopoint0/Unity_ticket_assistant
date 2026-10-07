import { useEffect, useState } from 'react';
import { api } from './api.js';
import Portal from './components/Portal.jsx';
import ChatWidget from './components/ChatWidget.jsx';

export default function App() {
  const [meta, setMeta] = useState(null);
  const [categories, setCategories] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [open, setOpen] = useState(false);
  const [seed, setSeed] = useState(null);

  useEffect(() => {
    api.meta().then(setMeta).catch(() => {});
    api.categories().then(setCategories).catch(() => {});
    api.tickets().then(setTickets).catch(() => {});
  }, []);

  // text = what the assistant receives; display = what the chat shows.
  const ask = (text, display) => {
    setOpen(true);
    if (text) setSeed({ text, display, at: Date.now() });
  };
  const raise = (offering) => ask(`service:${offering.id}`, `Raise a ticket: ${offering.name}`);

  return (
    <>
      <Portal meta={meta} categories={categories} tickets={tickets} onAsk={ask} onRaise={raise} />
      <ChatWidget meta={meta} open={open} onOpenChange={setOpen} seed={seed} />
    </>
  );
}
