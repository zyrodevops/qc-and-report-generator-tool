import React from 'react';
import { ParticularsBlock } from './ParticularsBlock';
import { TableBlock } from './TableBlock';
import { NarrativeBlock } from './NarrativeBlock';
import { MeasurementsBlock } from './MeasurementsBlock';
import { PhotoPlateBlock } from './PhotoPlateBlock';
import { ReconciliationBlock } from './ReconciliationBlock';

interface ScopedBlock {
  id: string;
  type: string;
  [key: string]: any;
}

interface ComputedUnit {
  unit_index: number;
  unit_id: string;
  identifier: string;
  heading: string;
  photo_ref?: string;
  blocks: ScopedBlock[];
}

interface UnitGroupBlockProps {
  block: {
    id: string;
    type: 'unit_group';
    heading_template?: string;
    _computed?: {
      unit_headings?: string[];
      units?: ComputedUnit[];
    };
    blocks?: ScopedBlock[];
  };
  reportId?: string;
}

export const UnitGroupBlock: React.FC<UnitGroupBlockProps> = ({ block, reportId }) => {
  const units = block._computed?.units || [];

  return (
    <div className="my-6 space-y-6">
      {units.map((unit) => (
        <div key={unit.unit_id} className="border-t-2 border-[#00387A] pt-3">
          <h2 className="text-[11pt] font-bold text-[#00387A] uppercase mb-3 tracking-wide">
            {unit.heading}
          </h2>
          <div className="space-y-4">
            {unit.blocks.map((b) => {
              if ((b as any).included === false) return null;
              switch (b.type) {
                case 'particulars':
                  return <ParticularsBlock key={b.id} block={b as any} />;
                case 'table':
                  return <TableBlock key={b.id} block={b as any} />;
                case 'reconciliation':
                  return <ReconciliationBlock key={b.id} block={b as any} />;
                case 'measurements':
                  return <MeasurementsBlock key={b.id} block={b as any} />;
                case 'photo_plate':
                  return <PhotoPlateBlock key={b.id} block={b as any} reportId={reportId} />;
                case 'narrative':
                  return <NarrativeBlock key={b.id} block={b as any} />;
                default:
                  return null;
              }
            })}
          </div>
        </div>
      ))}
    </div>
  );
};
