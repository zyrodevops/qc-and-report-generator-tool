/**
 * ClausePicker — standard wording for a narrative section, as topics.
 *
 * Each topic is one idea the client's reports carry in this section ("Pulp
 * temperature", "No recorder data", "Packing List"). Adding it puts in that
 * idea's sentences as the client writes them for this fruit and this
 * transport mode, in his layout (paragraphs and bullets). Several topics go
 * into one section; the cards are in the order the topics usually come, so
 * adding them left to right builds the section in the usual order. An added
 * topic can be removed again. Nothing is added unless the surveyor clicks,
 * and he can always just type.
 *
 * Facts from the report the wording came from are blanks — [DATE], [NAME],
 * [NUMBER] — filled only where this report already has the value.
 */
import React, { useEffect, useState } from 'react';
import { Check, ChevronDown, ChevronUp, Loader2, Plus, X } from 'lucide-react';
import { pickClauses, ClauseContext, WordingTopic } from '../../api/client';

// ---------------------------------------------------------------------------
// Section slug detection from heading text (shared utility)
// ---------------------------------------------------------------------------
export const HEADING_TO_SECTION: [RegExp, string][] = [
  [/application|appointment/i, 'application'],
  [/circumstance|circumstances of loss|attendance.*circumstance/i, 'circumstances_of_loss'],
  [/^\s*note\b|survey notes/i, 'note'],
  [/cause of loss|cause \& liability|cause.*damage/i, 'cause_of_loss'],
  [/our survey|survey.*finding|findings|condition found|the condition found|internal quality.*temperature/i, 'survey_findings'],
  [/next step/i, 'next_step'],
  [/document|annexure|enclosure/i, 'documentation'],
];

export function detectSectionFromHeading(heading: string): string {
  for (const [pattern, slug] of HEADING_TO_SECTION) {
    if (pattern.test(heading)) return slug;
  }
  return 'general';
}

/** Text with its blanks highlighted. */
export const WithBlanks: React.FC<{ text: string }> = ({ text }) => (
  <>
    {text.split(/(\[[^\]\n]{1,40}\])/g).map((part, i) =>
      /^\[[^\]]+\]$/.test(part) ? (
        <mark key={i} className="bg-amber-100 text-amber-900 rounded px-0.5 font-semibold">
          {part}
        </mark>
      ) : (
        <React.Fragment key={i}>{part}</React.Fragment>
      ),
    )}
  </>
);

export interface ClausePickerProps {
  /** Section heading as it appears on the form, e.g. "PARAGRAPH 3: CAUSE OF LOSS". */
  sectionHeading: string;
  /** What the report already knows — fruit, mode, container, measurements, defects. */
  context: ClauseContext;
  /** Topics already added to this section: topic key -> the text that was added. */
  added: Record<string, string>;
  onAdd: (topic: string, text: string) => void;
  onRemove: (topic: string) => void;
}

export const ClausePicker: React.FC<ClausePickerProps> = ({ sectionHeading, context, added, onAdd, onRemove }) => {
  const section = detectSectionFromHeading(sectionHeading);
  const [topics, setTopics] = useState<WordingTopic[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<string | null>(null);

  const contextKey = JSON.stringify(context);
  const hasFruit = Boolean(context.commodity);

  // Reload when what the report knows changes (a measurement typed in), so the
  // text added carries the latest figures. Debounced: not on every keystroke.
  useEffect(() => {
    if (!hasFruit || section === 'general') return;
    let cancelled = false;
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const res = await pickClauses(section, context);
        if (!cancelled) setTopics(res.topics);
      } catch {
        if (!cancelled) setTopics([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 400);
    return () => {
      cancelled = true;
      clearTimeout(t);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [section, contextKey]);

  if (section === 'general' || !hasFruit) return null;
  if (!topics?.length) {
    return loading ? (
      <div className="flex items-center gap-1.5 text-[10px] text-slate-400 mb-1.5">
        <Loader2 size={11} className="animate-spin" /> Loading standard wording…
      </div>
    ) : null;
  }

  const toggle = (t: WordingTopic) => {
    if (added[t.topic] !== undefined) onRemove(t.topic);
    else onAdd(t.topic, t.text);
    setPreview(null);
  };

  const cards = topics.filter((t) => !t.compact);
  const chips = topics.filter((t) => t.compact);
  const shown = topics.find((t) => t.topic === preview);

  return (
    <div className="mb-2">
      <div className="text-[10px] font-semibold uppercase tracking-wide text-slate-400 mb-1">
        Add standard wording
      </div>

      {cards.length > 0 && (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-1.5">
          {cards.map((t) => {
            const isAdded = added[t.topic] !== undefined;
            const open = preview === t.topic;
            return (
              <div
                key={t.topic}
                className={`rounded-md border px-2.5 py-1.5 transition ${
                  isAdded ? 'border-green-300 bg-green-50' : open ? 'border-blue-400 bg-blue-50' : 'border-slate-200 bg-white'
                }`}
                title={t.description}
              >
                <div className="flex items-start justify-between gap-1">
                  <span className="text-[11.5px] font-semibold text-slate-800 leading-tight">{t.label}</span>
                  {t.blanks.length > 0 && !isAdded && (
                    <span className="shrink-0 text-[9px] text-amber-700 bg-amber-50 border border-amber-200 rounded px-1">
                      {t.blanks.length} blank{t.blanks.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <button
                    type="button"
                    onClick={() => toggle(t)}
                    className={`inline-flex items-center gap-1 text-[10.5px] font-semibold px-1.5 py-0.5 rounded ${
                      isAdded ? 'text-red-700 bg-white border border-red-200 hover:bg-red-50' : 'text-white bg-blue-600 hover:bg-blue-700'
                    }`}
                  >
                    {isAdded ? <X size={10} /> : <Plus size={10} />}
                    {isAdded ? 'Remove' : 'Add'}
                  </button>
                  {isAdded ? (
                    <span className="inline-flex items-center gap-0.5 text-[10px] text-green-700">
                      <Check size={10} /> Added
                    </span>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setPreview(open ? null : t.topic)}
                      className="inline-flex items-center gap-0.5 text-[10.5px] text-blue-700 hover:text-blue-900"
                    >
                      {open ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                      {open ? 'Hide' : 'Preview'}
                    </button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {chips.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-1.5">
          {chips.map((t) => {
            const isAdded = added[t.topic] !== undefined;
            return (
              <button
                key={t.topic}
                type="button"
                onClick={() => toggle(t)}
                title={isAdded ? 'Remove from the list' : `Add “${t.text.replace(/^•\s*/, '')}”`}
                className={`inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border ${
                  isAdded
                    ? 'border-green-300 bg-green-50 text-green-800 hover:bg-red-50 hover:border-red-200 hover:text-red-700'
                    : 'border-slate-300 bg-white text-slate-700 hover:border-blue-400 hover:text-blue-700'
                }`}
              >
                {isAdded ? <Check size={10} /> : <Plus size={10} />}
                {t.label}
              </button>
            );
          })}
        </div>
      )}

      {shown && (
        <div className="mt-2 rounded-lg border border-blue-200 bg-white p-3">
          <div className="text-[11px] font-semibold text-blue-800 mb-1.5">{shown.label} — this is what will be added</div>
          <div className="text-[11px] leading-relaxed text-slate-700 whitespace-pre-line max-h-64 overflow-y-auto">
            <WithBlanks text={shown.text} />
          </div>
          <div className="flex items-center justify-between mt-2">
            <span className="text-[10px] text-slate-500">
              <mark className="bg-amber-100 text-amber-900 rounded px-0.5 font-semibold">[BRACKETS]</mark> are blanks to
              fill from this shipment.
            </span>
            <button
              type="button"
              onClick={() => toggle(shown)}
              className="inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-1 rounded text-white bg-blue-600 hover:bg-blue-700"
            >
              <Plus size={11} /> Add this
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
