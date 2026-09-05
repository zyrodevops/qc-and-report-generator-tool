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
              <table className="w-full border-collapse border border-gray-300 text-[9pt]">
                <thead>
                  <tr className="bg-[#00387A] text-white font-bold">
                    <th className="p-1.5 border border-gray-300 text-left">Part No.</th>
                    <th className="p-1.5 border border-gray-300 text-left">Description</th>
                    <th className="p-1.5 border border-gray-300 text-center">Qty</th>
                    <th className="p-1.5 border border-gray-300 text-left">Damage Findings</th>
                  </tr>
                </thead>
                <tbody>
                  {pkg.parts.map((p, pIdx) => {
                    const dmgStr = (p.damages || [])
                      .map(d => `${d.description}${d.severity ? ` (${d.severity})` : ''}`)
                      .join('; ') || 'None';
                    return (
                      <tr key={pIdx} className="border-b border-gray-300 hover:bg-slate-50">
                        <td className="p-1.5 border-r border-gray-300 font-mono">{p.part_no || '-'}</td>
                        <td className="p-1.5 border-r border-gray-300">{p.description}</td>
                        <td className="p-1.5 border-r border-gray-300 text-center">{p.quantity}</td>
                        <td className="p-1.5 border-gray-300 text-red-800">{dmgStr}</td>
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
