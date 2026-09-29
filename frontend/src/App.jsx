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

  const ask = (text) => {
    setOpen(true);
    if (text) setSeed({ text, at: Date.now() });
  };

  return (
    <>
      <Portal meta={meta} categories={categories} tickets={tickets} onAsk={ask} />
      <ChatWidget meta={meta} open={open} onOpenChange={setOpen} seed={seed} />
    </>
  );
}
