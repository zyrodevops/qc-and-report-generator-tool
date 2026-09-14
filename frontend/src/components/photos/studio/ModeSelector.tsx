import React from 'react';
import { Mode } from '../../../types/photoStudio';
import { FileText, Sliders, Layers } from 'lucide-react';

interface ModeSelectorProps {
  selectedMode: Mode;
  onModeSelect: (mode: Mode) => void;
}

export const ModeSelector: React.FC<ModeSelectorProps> = ({ selectedMode, onModeSelect }) => {
  const modes = [
    {
      id: 'normal' as Mode,
      title: 'Normal Mode',
      description: 'Upload exact count of images with captions in 2-column layout',
      icon: <FileText className="w-8 h-8 text-blue-600" />,
      badge: 'Fixed Layout',
    },
    {
      id: 'bulk' as Mode,
      title: 'Bulk Mode',
      description: 'Drag & drop batch upload with visual reordering and quick captions',
      icon: <Layers className="w-8 h-8 text-indigo-600" />,
      badge: 'Fast Batch',
    },
    {
      id: 'pro' as Mode,
      title: 'Pro Mode',
      description: 'Advanced options: compression presets, custom borders, auto-numbering & fonts',
      icon: <Sliders className="w-8 h-8 text-purple-600" />,
      badge: 'Custom Studio',
    },
  ];

  return (
    <div className="bg-white rounded-2xl shadow-xs border border-gray-200 p-6 mb-6">
      <div className="text-center max-w-lg mx-auto mb-6">
        <h2 className="text-xl font-bold text-gray-900">
          Select Photo Sheet Workflow
        </h2>
        <p className="text-xs text-gray-500 mt-1">
          Choose how you want to organize, caption, and export your survey photos
        </p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {modes.map((mode) => {
          const isSelected = selectedMode === mode.id;
          return (
            <button
              key={mode.id}
              type="button"
              onClick={() => onModeSelect(mode.id)}
              className={`
                relative p-5 rounded-xl border-2 text-left transition-all duration-200
                hover:scale-[1.02] hover:shadow-md cursor-pointer flex flex-col justify-between
                ${
                  isSelected
                    ? 'border-indigo-600 bg-indigo-50/50 shadow-sm'
                    : 'border-gray-200 bg-white hover:border-indigo-300'
                }
              `}
            >
              <div>
                <div className="flex justify-between items-start mb-3">
                  <div className="p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                    {mode.icon}
                  </div>
                  <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-gray-100 text-gray-700">
                    {mode.badge}
                  </span>
                </div>

                <h3 className="text-base font-bold text-gray-900 mb-1">
                  {mode.title}
                </h3>

                <p className="text-xs text-gray-600 leading-relaxed">
                  {mode.description}
                </p>
              </div>

              <div className="mt-4 pt-3 border-t border-gray-100 flex items-center justify-between text-xs">
                <span className={`font-semibold ${isSelected ? 'text-indigo-700' : 'text-gray-500'}`}>
                  {isSelected ? '✓ Selected' : 'Choose Mode →'}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default ModeSelector;
