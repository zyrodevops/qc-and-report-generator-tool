import React from 'react';

interface Damage {
  description: string;
  severity?: string;
}

interface Part {
  part_no?: string;
  description: string;
  quantity: number;
  damages?: Damage[];
}

interface Package {
  package_no: string;
  package_type: string;
  contents: string;
  parts?: Part[];
}

interface InventoryBlockProps {
  block: {
    id: string;
    type: 'inventory';
    packages?: Package[];
  };
}

export const InventoryBlock: React.FC<InventoryBlockProps> = ({ block }) => {
  const packages = block.packages || [];

  return (
    <div className="my-4 text-xs font-sans text-gray-800">
      <h2 className="text-[11pt] font-bold text-[#00387A] uppercase border-b border-gray-300 pb-1 mb-2 tracking-wide">
        Machinery & Package Damage Inventory
      </h2>
      {packages.length === 0 ? (
        <p className="italic text-gray-500">[No damaged items recorded]</p>
      ) : (
        packages.map((pkg, idx) => (
          <div key={idx} className="mb-4">
            <div className="font-bold text-gray-800 mb-1">
              Package {pkg.package_no}: {pkg.contents} ({pkg.package_type})
            </div>
            {pkg.parts && pkg.parts.length > 0 && (
              <table className="w-full border-collapse border border-gray-400 text-[9pt]">
                <thead>
                  <tr className="border-b border-gray-400 bg-white">
                    <th className="p-1.5 border border-gray-400 text-left font-bold text-gray-900">Part No.</th>
                    <th className="p-1.5 border border-gray-400 text-left font-bold text-gray-900">Description</th>
                    <th className="p-1.5 border border-gray-400 text-center font-bold text-gray-900">Qty</th>
                    <th className="p-1.5 border border-gray-400 text-left font-bold text-gray-900">Damage Findings</th>
                  </tr>
                </thead>
                <tbody>
                  {pkg.parts.map((p, pIdx) => {
                    const dmgStr = (p.damages || [])
                      .map(d => `${d.description}${d.severity ? ` (${d.severity})` : ''}`)
                      .join('; ') || 'None';
                    return (
                      <tr key={pIdx} className="border-b border-gray-400 hover:bg-slate-50/50">
                        <td className="p-1.5 border border-gray-400 font-mono text-gray-900">{p.part_no || '-'}</td>
                        <td className="p-1.5 border border-gray-400 text-gray-800">{p.description}</td>
                        <td className="p-1.5 border border-gray-400 text-center text-gray-800">{p.quantity}</td>
                        <td className="p-1.5 border border-gray-400 text-red-800">{dmgStr}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        ))
      )}
    </div>
  );
};
