import React, { useState } from 'react';
import { AlertTriangle, Loader2, PenLine, Sparkles } from 'lucide-react';
import { ClauseContext, draftFromNotes, NotesDraft } from '../../api/client';

interface Props {
  section: string;
  context: ClauseContext;
  /** Adds the text to the end of the section. */
  onAdd: (text: string) => void;
}

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

/** The text, with what was not in the notes marked in red. */
const Marked: React.FC<{ text: string; flagged: string[] }> = ({ text, flagged }) => {
  if (!flagged.length) return <>{text}</>;
  const rx = new RegExp(`(${flagged.map(escape).join('|')})`, 'g');
  return (
    <>
      {text.split(rx).map((part, i) =>
        flagged.includes(part) ? (
          <mark key={i} className="bg-red-100 text-red-800 rounded px-0.5 font-semibold">{part}</mark>
        ) : (
          <React.Fragment key={i}>{part}</React.Fragment>
        ),
      )}
    </>
  );
};

/**
 * Short notes in, report text out. The text is written by Gemini in the
 * wording of this section's standard sentences, using only the notes and the
 * report's own facts. Anything it states that is not in them is marked in red.
 * When no model answers, the notes come back as typed; nothing is lost.
 */
export const NotesWriter: React.FC<Props> = ({ section, context, onAdd }) => {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState<NotesDraft | null>(null);
  const [error, setError] = useState('');

  const write = async () => {
    setBusy(true);
    setError('');
    setDraft(null);
    try {
      setDraft(await draftFromNotes(section, context, notes));
    } catch (e: any) {
      setError(e?.message || 'Could not write from the notes.');
    } finally {
      setBusy(false);
    }
  };

  const add = (text: string) => {
    onAdd(text);
    setDraft(null);
    setNotes('');
    setOpen(false);
  };

  if (!open) {
    return (
      <button type="button" onClick={() => setOpen(true)}
        className="mt-1 inline-flex items-center gap-1 text-[11px] text-violet-700 hover:text-violet-900">
        <Sparkles size={11} /> Write from my notes
      </button>
    );
  }
  const fromAi = draft && draft.source !== 'notes';
  return (
    <div className="mt-2 rounded-lg border border-violet-200 bg-violet-50/40 p-3 space-y-2" data-testid="notes-writer">
      <div className="text-[11px] font-semibold text-violet-900">Write from my notes</div>
      <textarea
        aria-label="Notes"
        value={notes}
        onChange={(e) => setNotes(e.target.value)}
        rows={3}
        placeholder="Short notes, e.g. 45 bags wet bottom tier, seal intact, CHA Mr. Shah present"
        className="w-full text-xs border border-violet-200 rounded p-2 bg-white focus:outline-none focus:ring-1 focus:ring-violet-400"
      />
      <div className="flex items-center gap-2">
        <button type="button" disabled={busy || !notes.trim()} onClick={write}
          className="inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded text-white bg-violet-600 hover:bg-violet-700 disabled:opacity-50">
          {busy ? <Loader2 size={12} className="animate-spin" /> : <PenLine size={12} />}
          {busy ? 'Writing…' : 'Write it'}
        </button>
        <button type="button" onClick={() => { setOpen(false); setDraft(null); }} className="text-[11px] text-slate-500 hover:text-slate-700">
          Close
        </button>
        {error && <span className="text-[11px] text-red-700">{error}</span>}
      </div>

      {draft && (
        <div className="rounded border border-violet-200 bg-white p-2.5 space-y-2" data-testid="notes-draft">
          <div className="text-[10.5px] text-violet-800 font-semibold">
            {fromAi ? 'Written by AI from your notes. Read it before adding.' : 'Your notes, as typed.'}
          </div>
          {draft.message && <div className="text-[10.5px] text-amber-800">{draft.message}</div>}
          <div className="text-[11px] leading-relaxed text-slate-700 whitespace-pre-line">
            <Marked text={draft.text} flagged={draft.flagged} />
          </div>
          {(draft.removed || []).length > 0 && (
            <div className="text-[10.5px] text-slate-600 border-t border-slate-100 pt-1.5" data-testid="notes-removed">
              <span className="font-semibold">Left out (your notes do not say this):</span>
              <ul className="list-disc pl-4 mt-0.5 line-through decoration-slate-400">
                {draft.removed!.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          )}
          {draft.flagged.length > 0 && (
            <div className="flex items-start gap-1 text-[10.5px] text-red-800">
              <AlertTriangle size={12} className="shrink-0 mt-0.5" />
              <span>Not in your notes or the report: {draft.flagged.join(', ')}. Check or correct these after adding.</span>
            </div>
          )}
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => add(draft.text)}
              className="text-xs font-semibold px-2.5 py-1 rounded text-white bg-blue-600 hover:bg-blue-700">
              Add this
            </button>
            {fromAi && (
              <button type="button" onClick={() => add(notes.trim())} className="text-[11px] text-slate-600 hover:text-slate-900">
                Add my notes as typed instead
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotesWriter;
