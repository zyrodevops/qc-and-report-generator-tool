/**
 * ClauseLibraryPicker — legacy re-export shim.
 *
 * The clause library has been split into three section-aware components:
 *   - CauseOfLossPicker  (cause_of_loss sections)  → components/clauses/CauseOfLossPicker.tsx
 *   - NextStepPicker     (next_step sections)        → components/clauses/NextStepPicker.tsx
 *   - BoilerplatePicker  (all other sections)        → components/clauses/BoilerplatePicker.tsx
 *
 * NarrativeBlock.tsx now imports directly from those components and routes
 * to the correct one based on the section slug.
 *
 * This file re-exports BoilerplatePicker under the old name so any external
 * imports of ClauseLibraryPicker continue to compile without changes.
 *
 * Path note: this file lives at src/components/preview/blocks/
 *            the new components live at  src/components/clauses/
 *            therefore the relative path is ../../clauses/
 */
export {
  BoilerplatePicker as ClauseLibraryPicker,
  detectSectionFromHeading,
  SECTION_LABELS,
  HEADING_TO_SECTION,
} from '../../clauses/BoilerplatePicker';

export type { BoilerplatePickerProps as ClauseLibraryPickerProps } from '../../clauses/BoilerplatePicker';
