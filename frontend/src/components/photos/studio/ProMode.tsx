import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  ImageData,
  ProModeOptions,
  DEFAULT_PRO_OPTIONS,
  FONT_TYPES,
  FONT_SIZES,
  FONT_COLORS,
  BOX_COLORS,
  MAX_IMAGE_COUNT,
  AUTO_NUMBER_KEYWORDS,
  COMPRESSION_PRESETS,
  CompressionPreset,
  estimatedDocxSize,
} from '../../../types/photoStudio';
import { processImage, rotateImage } from '../../../utils/imageProcessor';
import { generateProModeDocx, generateFileName } from '../../../utils/docxGenerator';
import { formatAutoCaption, stripPhotoPrefix } from '../../../utils/captionUtils';
import { Download, Settings, Upload, X, ArrowRight, RotateCcw } from 'lucide-react';

interface ProModeProps {
  /** The chosen options go too, and become how the report prints the photos. */
  onSendToReport?: (photos: ImageData[], options?: ProModeOptions) => Promise<void>;
  reportId?: string;
}

export const ProMode: React.FC<ProModeProps> = ({ onSendToReport, reportId }) => {
  const [images, setImages] = useState<ImageData[]>([]);
  const [proOptions, setProOptions] = useState<ProModeOptions>(DEFAULT_PRO_OPTIONS);
  const [showConfig, setShowConfig] = useState<boolean>(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const effectiveKeyword = proOptions.isCustomKeyword
    ? (proOptions.customKeyword || 'Photo')
    : proOptions.autoNumberKeyword;

  const startNum = proOptions.useCustomNumberStart ? (proOptions.numberStartFrom || 1) : 1;

  const onDrop = async (acceptedFiles: File[]) => {
    if (images.length + acceptedFiles.length > MAX_IMAGE_COUNT) {
      alert(`Maximum ${MAX_IMAGE_COUNT} images allowed.`);
      return;
    }

    setIsProcessing(true);
    const startingIndex = images.length;
    const { maxDimension, quality } = COMPRESSION_PRESETS[proOptions.compressionPreset];

    const newImagesPromises = acceptedFiles.map(async (file, index) => {
      try {
        const processed = await processImage(
          file,
          proOptions.compressionEnabled,
          maxDimension,
          quality
        );
        
        const autoDescription = proOptions.autoNumberDescription 
          ? formatAutoCaption('', startingIndex + index, { keyword: effectiveKeyword, startNum })
          : '';
        
        return {
          id: `${Date.now()}-${Math.random()}`,
          file,
          preview: processed.preview,
          description: autoDescription,
          rotated: processed.wasRotated,
          processedBlob: processed.blob,
          originalOrientation: processed.originalOrientation,
          dimensions: {
            width: processed.width,
            height: processed.height,
          },
        } as ImageData;
      } catch (error) {
        console.error(`Failed to process ${file.name}:`, error);
        return null;
      }
    });

    const processedImages = await Promise.all(newImagesPromises);
    const validImages = processedImages.filter((img): img is ImageData => img !== null);

    setImages((prev) => [...prev, ...validImages]);
    setIsProcessing(false);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
      'image/bmp': ['.bmp'],
    },
    multiple: true,
  });

  const handleDescriptionChange = (index: number, description: string) => {
    const newImages = [...images];
    if (newImages[index]) {
      newImages[index].description = description;
      setImages(newImages);
    }
  };

  const handleAutoNumberToggle = (enabled: boolean) => {
    setProOptions({ ...proOptions, autoNumberDescription: enabled });
    if (enabled) {
      const updatedImages = images.map((img, index) => ({
        ...img,
        description: formatAutoCaption(img.description || '', index, {
          keyword: effectiveKeyword,
          startNum,
        }),
      }));
      setImages(updatedImages);
    } else {
      // Strip photo number prefixes cleanly
      const updatedImages = images.map((img) => ({
        ...img,
        description: stripPhotoPrefix(img.description || ''),
      }));
      setImages(updatedImages);
    }
  };

  const handleKeywordChange = (keyword: string) => {
    setProOptions({ ...proOptions, autoNumberKeyword: keyword, isCustomKeyword: false });
    if (proOptions.autoNumberDescription) {
      const updatedImages = images.map((img, index) => ({
        ...img,
        description: formatAutoCaption(img.description || '', index, {
          keyword,
          startNum,
        }),
      }));
      setImages(updatedImages);
    }
  };

  const handleCustomKeywordChange = (value: string) => {
    setProOptions({ ...proOptions, customKeyword: value, isCustomKeyword: true });
    if (proOptions.autoNumberDescription) {
      const updatedImages = images.map((img, index) => ({
        ...img,
        description: formatAutoCaption(img.description || '', index, {
          keyword: value || 'Photo',
          startNum,
        }),
      }));
      setImages(updatedImages);
    }
  };

  const handleNumberStartChange = (value: number, enabled: boolean) => {
    const newStart = enabled ? (value || 1) : 1;
    setProOptions({ ...proOptions, useCustomNumberStart: enabled, numberStartFrom: value });
    if (proOptions.autoNumberDescription) {
      const updatedImages = images.map((img, index) => ({
        ...img,
        description: formatAutoCaption(img.description || '', index, {
          keyword: effectiveKeyword,
          startNum: newStart,
        }),
      }));
      setImages(updatedImages);
    }
  };

  const handleRotate = async (index: number) => {
    const imageData = images[index];
    if (!imageData || !imageData.processedBlob) return;

    try {
      const { quality } = COMPRESSION_PRESETS[proOptions.compressionPreset];
      const currentRotation = imageData.rotationAngle || 0;
      const rotated = await rotateImage(imageData.processedBlob, currentRotation, quality);

      if (imageData.preview) {
        URL.revokeObjectURL(imageData.preview);
      }

      const newImages = [...images];
      newImages[index] = {
        ...imageData,
        preview: rotated.preview,
        processedBlob: rotated.blob,
        dimensions: {
          width: rotated.width,
          height: rotated.height,
        },
        rotationAngle: rotated.rotation,
      };
      setImages(newImages);
    } catch (error) {
      console.error('Error rotating image:', error);
      alert('Failed to rotate image.');
    }
  };

  const handleDownloadDocx = async () => {
    const validImages = images.filter((img) => img.file && img.processedBlob);
    if (validImages.length === 0) {
      alert('Please upload at least one image before downloading.');
      return;
    }

    setIsGenerating(true);
    try {
      const fileName = generateFileName('Marine_Cargo_Report_Pro');
      await generateProModeDocx(validImages, proOptions, fileName);
    } catch (error: any) {
      console.error('Failed to generate DOCX:', error);
      alert(`Failed to generate document: ${error?.message || 'Unknown error'}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSendToReport = async () => {
    const validImages = images.filter((img) => img.file && img.processedBlob);
    if (validImages.length === 0) {
      alert('No photos to send.');
      return;
    }
    if (!onSendToReport) return;

    setIsSending(true);
    try {
      await onSendToReport(validImages, proOptions);
    } catch (err: any) {
      alert(`Failed to save to report: ${err?.message || err}`);
    } finally {
      setIsSending(false);
    }
  };

  const handleRemoveImage = (index: number) => {
    const newImages = [...images];
    if (newImages[index]?.preview) {
      URL.revokeObjectURL(newImages[index].preview);
    }
    newImages.splice(index, 1);
    if (proOptions.autoNumberDescription) {
      const renumbered = newImages.map((img, idx) => ({
        ...img,
        description: formatAutoCaption(img.description || '', idx, {
          keyword: effectiveKeyword,
          startNum,
        }),
      }));
      setImages(renumbered);
    } else {
      setImages(newImages);
    }
  };

  return (
    <div className="space-y-6">
      {/* Configuration Header Card */}
      <div className="bg-white rounded-xl shadow-xs border border-gray-200 p-5">
        <div className="flex items-center justify-between pb-3 border-b border-gray-100">
          <div>
            <h3 className="text-base font-bold text-gray-900">Pro Mode Studio Settings</h3>
            <p className="text-xs text-gray-500">Customize output document styling, compression, borders, and numbering</p>
          </div>
          <button
            type="button"
            onClick={() => setShowConfig(!showConfig)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg text-xs font-semibold transition"
          >
            <Settings className="w-3.5 h-3.5" />
            {showConfig ? 'Hide Settings' : 'Show Settings'}
          </button>
        </div>

        {showConfig && (
          <div className="pt-4 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 text-xs">
            {/* Compression */}
            <div className="space-y-2 lg:col-span-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <div className="flex items-center justify-between">
                <label className="font-bold text-gray-800">
                  📦 Standalone Compression Preset
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={proOptions.compressionEnabled}
                    onChange={(e) => setProOptions({ ...proOptions, compressionEnabled: e.target.checked })}
                    className="rounded text-indigo-600 focus:ring-indigo-500"
                  />
                  <span className="font-semibold text-gray-700">
                    {proOptions.compressionEnabled ? 'Enabled' : 'Disabled (Original Quality)'}
                  </span>
                </label>
              </div>

              {proOptions.compressionEnabled && (
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 pt-2">
                  {(Object.entries(COMPRESSION_PRESETS) as [CompressionPreset, typeof COMPRESSION_PRESETS[CompressionPreset]][]).map(
                    ([key, cfg]) => (
                      <label
                        key={key}
                        className={`p-2.5 rounded-lg border cursor-pointer transition flex flex-col justify-between ${
                          proOptions.compressionPreset === key
                            ? 'border-indigo-600 bg-indigo-50/50 text-indigo-900'
                            : 'border-gray-200 bg-white hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <input
                            type="radio"
                            name="compressionPreset"
                            value={key}
                            checked={proOptions.compressionPreset === key}
                            onChange={() => setProOptions({ ...proOptions, compressionPreset: key })}
                            className="text-indigo-600"
                          />
                          <span className="font-bold">{cfg.label}</span>
                        </div>
                        <span className="text-[11px] text-gray-500 mt-1">{cfg.description}</span>
                        <span className="text-[10px] text-gray-400 font-mono mt-0.5">
                          {cfg.maxDimension}px • q={cfg.quality}
                        </span>
                      </label>
                    )
                  )}
                </div>
              )}
            </div>

            {/* Borders & Styling */}
            <div className="space-y-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <label className="flex items-center justify-between cursor-pointer font-bold text-gray-800">
                <span>Add Cell Borders</span>
                <input
                  type="checkbox"
                  checked={proOptions.addBorder}
                  onChange={(e) => setProOptions({ ...proOptions, addBorder: e.target.checked })}
                  className="rounded text-indigo-600"
                />
              </label>

              {proOptions.addBorder && (
                <div>
                  <label className="block text-gray-600 font-medium mb-1">Border Color</label>
                  <select
                    value={proOptions.boxColor}
                    onChange={(e) => setProOptions({ ...proOptions, boxColor: e.target.value })}
                    className="w-full bg-white border border-gray-300 rounded-lg p-1.5 text-xs outline-none"
                  >
                    {BOX_COLORS.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.name}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </div>

            {/* Auto-Numbering */}
            <div className="space-y-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <label className="flex items-center justify-between cursor-pointer font-bold text-gray-800">
                <span>Auto-Number Captions</span>
                <input
                  type="checkbox"
                  checked={proOptions.autoNumberDescription}
                  onChange={(e) => handleAutoNumberToggle(e.target.checked)}
                  className="rounded text-indigo-600"
                />
              </label>

              {proOptions.autoNumberDescription && (
                <div className="space-y-2">
                  <div>
                    <label className="block text-gray-600 font-medium mb-1">Caption Prefix</label>
                    <select
                      value={proOptions.isCustomKeyword ? 'custom' : proOptions.autoNumberKeyword}
                      onChange={(e) => {
                        if (e.target.value === 'custom') {
                          setProOptions({ ...proOptions, isCustomKeyword: true });
                        } else {
                          handleKeywordChange(e.target.value);
                        }
                      }}
                      className="w-full bg-white border border-gray-300 rounded-lg p-1.5 text-xs outline-none mb-1.5"
                    >
                      {AUTO_NUMBER_KEYWORDS.map((k) => (
                        <option key={k} value={k}>
                          {k}
                        </option>
                      ))}
                      <option value="custom">Custom Prefix...</option>
                    </select>

                    {proOptions.isCustomKeyword && (
                      <input
                        type="text"
                        value={proOptions.customKeyword}
                        onChange={(e) => handleCustomKeywordChange(e.target.value)}
                        placeholder="e.g., Damage Photo No."
                        className="w-full bg-white border border-gray-300 rounded-lg p-1.5 text-xs outline-none"
                      />
                    )}
                  </div>

                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-1.5 text-gray-600">
                      <input
                        type="checkbox"
                        checked={proOptions.useCustomNumberStart}
                        onChange={(e) => handleNumberStartChange(proOptions.numberStartFrom, e.target.checked)}
                        className="rounded text-indigo-600"
                      />
                      <span>Start from:</span>
                    </label>
                    {proOptions.useCustomNumberStart && (
                      <input
                        type="number"
                        min={1}
                        value={proOptions.numberStartFrom}
                        onChange={(e) => handleNumberStartChange(parseInt(e.target.value, 10) || 1, true)}
                        className="w-16 bg-white border border-gray-300 rounded p-1 text-xs outline-none text-center"
                      />
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Typography */}
            <div className="space-y-3 p-3 bg-slate-50 rounded-xl border border-slate-200">
              <span className="block font-bold text-gray-800">Typography</span>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-gray-500 mb-0.5">Font</label>
                  <select
                    value={proOptions.fontType}
                    onChange={(e) => setProOptions({ ...proOptions, fontType: e.target.value })}
                    className="w-full bg-white border border-gray-300 rounded-lg p-1 text-xs outline-none"
                  >
                    {FONT_TYPES.map((f) => (
                      <option key={f} value={f}>{f}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-gray-500 mb-0.5">Size</label>
                  <select
                    value={proOptions.fontSize}
                    onChange={(e) => setProOptions({ ...proOptions, fontSize: parseInt(e.target.value, 10) })}
                    className="w-full bg-white border border-gray-300 rounded-lg p-1 text-xs outline-none"
                  >
                    {FONT_SIZES.map((s) => (
                      <option key={s} value={s}>{s} pt</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-gray-500 mb-0.5">Color</label>
                <select
                  value={proOptions.fontColor}
                  onChange={(e) => setProOptions({ ...proOptions, fontColor: e.target.value })}
                  className="w-full bg-white border border-gray-300 rounded-lg p-1 text-xs outline-none"
                >
                  {FONT_COLORS.map((c) => (
                    <option key={c.value} value={c.value}>{c.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-3 border-dashed rounded-2xl p-8 text-center transition-all cursor-pointer ${
          isDragActive
            ? 'border-indigo-600 bg-indigo-50/60 scale-[1.01]'
            : 'border-gray-300 hover:border-indigo-500 hover:bg-slate-50'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-2">
          <Upload className="w-8 h-8 text-indigo-600" />
          <p className="text-sm font-bold text-gray-800">
            Drop Images into Pro Studio
          </p>
          <p className="text-xs text-gray-500">
            Estimated DOCX size: {estimatedDocxSize(images.length, proOptions.compressionPreset)}
          </p>
          {isProcessing && (
            <div className="flex items-center gap-1.5 text-xs text-indigo-600 mt-2">
              <div className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-indigo-600 border-t-transparent"></div>
              <span>Processing photos...</span>
            </div>
          )}
        </div>
      </div>

      {/* Action Bar & Grid */}
      {images.length > 0 && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <span className="text-sm font-bold text-gray-800">
              {images.length} Photos Configured
            </span>

            <div className="flex items-center gap-2">
              {onSendToReport && reportId && (
                <button
                  type="button"
                  onClick={handleSendToReport}
                  disabled={isSending}
                  className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-xs"
                >
                  <ArrowRight className="w-3.5 h-3.5" />
                  {isSending ? 'Sending...' : 'Attach to Active Report'}
                </button>
              )}

              <button
                type="button"
                onClick={handleDownloadDocx}
                disabled={isGenerating}
                className="px-4 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 shadow-xs disabled:opacity-40"
              >
                <Download className="w-3.5 h-3.5" />
                {isGenerating ? 'Generating...' : 'Download Pro DOCX'}
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {images.map((image, index) => (
              <div
                key={image.id}
                className="relative bg-white border border-gray-200 rounded-xl overflow-hidden shadow-xs hover:border-indigo-400 transition"
              >
                <div className="absolute top-2 left-2 bg-indigo-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full z-10 shadow-xs">
                  #{index + startNum}
                </div>

                <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
                  {image.rotated && (
                    <button
                      type="button"
                      onClick={() => handleRotate(index)}
                      className="bg-blue-600 hover:bg-blue-700 text-white p-1 rounded-full shadow-xs transition-colors"
                      title="Rotate 90°"
                    >
                      <RotateCcw size={12} />
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => handleRemoveImage(index)}
                    className="bg-red-600 text-white p-1 rounded-full hover:bg-red-700 transition-colors shadow-xs"
                    title="Remove photo"
                  >
                    <X size={12} />
                  </button>
                </div>

                <div className="aspect-square bg-slate-50 flex items-center justify-center">
                  {image.preview && (
                    <img
                      src={image.preview}
                      alt={`Photo ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                  )}
                </div>

                <div className="p-2 bg-white border-t border-gray-100 space-y-1">
                  <input
                    type="text"
                    value={image.description || ''}
                    onChange={(e) => handleDescriptionChange(index, e.target.value)}
                    placeholder="Caption..."
                    className="w-full text-xs px-2 py-1 border border-gray-200 rounded focus:ring-1 focus:ring-indigo-500 outline-none"
                  />
                  <p className="text-[10px] text-gray-400 truncate">
                    {image.file.name}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default ProMode;
