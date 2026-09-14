import React, { ChangeEvent, useRef } from 'react';
import { X, Upload, Image as ImageIcon, RotateCw, RotateCcw } from 'lucide-react';
import { ImageData } from '../../../types/photoStudio';
import { getFileSizeDisplay } from '../../../utils/imageProcessor';

interface ImageUploadBoxProps {
  index: number;
  imageData: ImageData | null;
  onImageUpload: (index: number, file: File) => void;
  onDescriptionChange: (index: number, description: string) => void;
  onClear: (index: number) => void;
  onRotate?: (index: number) => void;
  hideDescription?: boolean;
}

export const ImageUploadBox: React.FC<ImageUploadBoxProps> = ({
  index,
  imageData,
  onImageUpload,
  onDescriptionChange,
  onClear,
  onRotate,
  hideDescription = false,
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      onImageUpload(index, file);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 hover:border-indigo-500 transition-all duration-200 hover:shadow-md">
      {/* Box Number */}
      <div className="flex justify-between items-center mb-3">
        <span className="text-xs font-bold text-white bg-indigo-600 px-2.5 py-1 rounded-full">
          Photo #{index + 1}
        </span>
        {imageData && (
          <button
            onClick={() => onClear(index)}
            className="text-gray-400 hover:text-red-600 hover:bg-red-50 p-1 rounded transition-colors"
            title="Clear photo"
          >
            <X size={16} />
          </button>
        )}
      </div>

      {/* Image Preview Area */}
      <div className="mb-3">
        {imageData ? (
          <div className="relative w-full h-44 bg-slate-50 border border-gray-200 rounded-lg overflow-hidden group flex items-center justify-center">
            <img
              src={imageData.preview}
              alt={`Preview ${index + 1}`}
              className="w-full h-full object-contain"
            />
            {/* Rotation indicator and button */}
            {imageData.rotated && (
              <div className="absolute top-2 right-2 flex items-center gap-1.5">
                <div className="bg-emerald-600 text-white px-2 py-0.5 rounded text-[11px] font-semibold flex items-center gap-1 shadow-sm">
                  <RotateCw size={11} />
                  Auto-rotated
                </div>
                {onRotate && (
                  <button
                    onClick={() => onRotate(index)}
                    className="bg-blue-600 hover:bg-blue-700 text-white p-1 rounded shadow-sm transition-colors"
                    title="Rotate 90° anti-clockwise"
                  >
                    <RotateCcw size={12} />
                  </button>
                )}
              </div>
            )}
            {/* Image info overlay on hover */}
            <div className="absolute bottom-0 left-0 right-0 bg-slate-900/80 text-white p-2 text-[11px] opacity-0 group-hover:opacity-100 transition-opacity">
              <p>Size: {getFileSizeDisplay(imageData.file.size)}</p>
              {imageData.dimensions && (
                <p>Dimensions: {imageData.dimensions.width} × {imageData.dimensions.height} px</p>
              )}
              {imageData.originalOrientation && (
                <p>Original: {imageData.originalOrientation}</p>
              )}
            </div>
          </div>
        ) : (
          <div
            onClick={handleUploadClick}
            className="w-full h-44 bg-slate-50 border-2 border-dashed border-gray-300 rounded-lg flex flex-col items-center justify-center cursor-pointer hover:border-indigo-500 hover:bg-indigo-50/30 transition-all"
          >
            <ImageIcon size={36} className="text-gray-400 mb-2" />
            <p className="text-xs text-gray-700 font-semibold">Click to select photo</p>
            <p className="text-[10px] text-gray-400 mt-0.5">JPG, PNG, BMP</p>
          </div>
        )}
      </div>

      {/* Upload Button */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileSelect}
        accept="image/jpeg,image/jpg,image/png,image/bmp"
        className="hidden"
        aria-label={`Upload image ${index + 1}`}
      />
      
      <button
        onClick={handleUploadClick}
        className={`w-full py-1.5 px-3 rounded-lg text-xs font-semibold transition-all ${hideDescription ? '' : 'mb-2.5'} flex items-center justify-center gap-1.5 ${
          imageData
            ? 'bg-gray-100 text-gray-700 hover:bg-gray-200 border border-gray-300'
            : 'bg-indigo-600 text-white hover:bg-indigo-700 shadow-sm'
        }`}
      >
        <Upload size={14} />
        {imageData ? 'Change Photo' : 'Select Photo'}
      </button>

      {/* Description Textarea */}
      {!hideDescription && (
        <>
          <textarea
            placeholder="Observation or caption..."
            value={imageData?.description || ''}
            onChange={(e) => onDescriptionChange(index, e.target.value)}
            className="w-full px-2.5 py-1.5 border border-gray-300 rounded-lg resize-none focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-xs text-gray-800"
            rows={2}
          />
          {imageData?.description && (
            <p className="text-[10px] text-gray-400 mt-0.5 text-right">
              {imageData.description.length} chars
            </p>
          )}
        </>
      )}
    </div>
  );
};

export default ImageUploadBox;
