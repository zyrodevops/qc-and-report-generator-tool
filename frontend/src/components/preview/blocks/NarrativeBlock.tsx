import React, { useRef, useLayoutEffect, useState } from 'react';
import { detectSectionFromHeading, SECTION_LABELS } from '../../clauses/BoilerplatePicker';
import { CauseOfLossPicker } from '../../clauses/CauseOfLossPicker';
import { NextStepPicker } from '../../clauses/NextStepPicker';
import { BoilerplatePicker } from '../../clauses/BoilerplatePicker';
import { ScenarioPicker } from '../../clauses/ScenarioPicker';


export interface NarrativeBlockProps {
  block: any;
  onChange?: (updatedBlock: any) => void;
  editable?: boolean;
  /** Commodity key (e.g. "APPLE") passed down from ReportPreview via blockState.metadata */
  commodity?: string;
}

export const NarrativeBlock: React.FC<NarrativeBlockProps> = ({
  block,
  onChange,
  editable = true,
  commodity,
}) => {
  const sectionTitle = block?.section || 'ATTENDANCE & CIRCUMSTANCES';
  const text = block?.additional_text || '';
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  // Track which cause key was last selected (for CauseOfLossPicker visual state)
  const [selectedCauseKey, setSelectedCauseKey] = useState<string | null>(
    block?._cause_key ?? null
  );

  // useLayoutEffect fires synchronously after DOM mutation but before browser paint,
  // so the resize happens immediately even when text is set programmatically
  // (e.g. clause insertion), preventing overflow-hidden from clipping content.
  useLayoutEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.max(80, el.scrollHeight)}px`;
  }, [text, editable]);

  if (!text && !sectionTitle && !editable) return null;

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    if (!onChange) return;
    onChange({
      ...block,
      additional_text: e.target.value,
      surveyor_edited: true,
    });
  };

  /** Append text to the textarea (with double newline separator) */
  const handleInsertClause = (clauseText: string) => {
    if (!onChange) return;
    const current = text.trim();
    const newText = current ? `${current}\n\n${clauseText}` : clauseText;
    onChange({
      ...block,
      additional_text: newText,
      surveyor_edited: true,
    });
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
        textareaRef.current.selectionStart = textareaRef.current.value.length;
        textareaRef.current.selectionEnd = textareaRef.current.value.length;
      }
    }, 50);
  };

  /** Called when CauseOfLossPicker selects a cause — replaces block text entirely */
  const handleCauseSelect = (wording: string, causeKey: string) => {
    if (!onChange) return;
    setSelectedCauseKey(causeKey);
    onChange({
      ...block,
      additional_text: wording,
      _cause_key: causeKey,
      surveyor_edited: true,
    });
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }, 50);
  };

  /** Called when ScenarioPicker selects a full scenario paragraph */
  const handleScenarioSelect = (scenarioText: string) => {
    if (!onChange) return;
    onChange({
      ...block,
      additional_text: scenarioText,
      surveyor_edited: true,
    });
    setTimeout(() => {
      if (textareaRef.current) {
        textareaRef.current.focus();
      }
    }, 50);
  };

  /** Called when NextStepPicker assembles actions */
  const handleNextStepAssemble = (assembled: string) => {
    handleInsertClause(assembled);
  };

  // Detect which section we're in
  const sectionSlug = detectSectionFromHeading(sectionTitle);
  const isScenarioSection = ['circumstances_of_loss', 'note', 'survey_findings', 'application', 'documentation'].includes(sectionSlug);

  // Split and highlight bracketed photo references (Photo Nos?...)
  const renderFormattedText = (content: string) => {
    const parts = content.split(/(\(Photo Nos?\. [^\)]+\))/g);
    return parts.map((part, i) => {
      if (/^\(Photo Nos?\. [^\)]+\)$/.test(part)) {
        return (
          <span key={i} className="font-mono font-bold text-[#00387A]">
            {part}
          </span>
        );
      }
      return part;
    });
  };

  const paragraphs = text.split('\n\n').filter(Boolean);

  return (
    <div className="narrative-block my-2">
      {sectionTitle && (
        <h2 className="text-[12px] font-bold text-[#00387A] uppercase tracking-wider border-b border-slate-300 pb-1 mb-2">
          {sectionTitle}
        </h2>
      )}
      {editable && onChange ? (
        <>
          {/* ── Smart clause pickers — section-aware routing ── */}
          <div className="flex flex-wrap items-center gap-2 mb-1">
            {sectionSlug === 'cause_of_loss' ? (
              <CauseOfLossPicker
                commodity={commodity}
                selectedKey={selectedCauseKey}
                onSelect={handleCauseSelect}
              />
            ) : sectionSlug === 'next_step' ? (
              <NextStepPicker
                commodity={commodity}
                onAssemble={handleNextStepAssemble}
              />
            ) : isScenarioSection ? (
              <>
                <ScenarioPicker
                  commodity={commodity}
                  sectionSlug={sectionSlug}
                  sectionLabel={SECTION_LABELS[sectionSlug] || 'Section'}
                  onSelect={handleScenarioSelect}
                />
                <BoilerplatePicker
                  commodity={commodity}
                  sectionHeading={sectionTitle}
                  onInsert={handleInsertClause}
                />
              </>
            ) : (
              <BoilerplatePicker
                commodity={commodity}
                sectionHeading={sectionTitle}
                onInsert={handleInsertClause}
              />
            )}
          </div>


          <textarea
            ref={textareaRef}
            value={text}
            onChange={handleTextChange}
            placeholder={
              sectionSlug === 'cause_of_loss'
                ? 'Select a cause pattern above, or type your cause-of-loss analysis…'
                : sectionSlug === 'next_step'
                ? 'Select next-step actions above, or type your recommendations…'
                : 'Click to enter findings and circumstances, or use Clause Library above…'
            }
            className="w-full bg-transparent border border-transparent hover:border-blue-200 focus:border-blue-500 focus:bg-white focus:outline-none rounded p-1 text-xs leading-relaxed text-slate-800 text-justify font-sans resize-none overflow-hidden transition-colors cursor-text"
          />
        </>
      ) : (
        <div className="space-y-2 text-xs leading-relaxed text-slate-800 text-justify">
          {paragraphs.length > 0 ? (
            paragraphs.map((p: string, idx: number) => (
              <p key={idx}>{renderFormattedText(p)}</p>
            ))
          ) : (
            <p>{renderFormattedText(text)}</p>
          )}
        </div>
      )}
    </div>
  );
};
