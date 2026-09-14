import React, { useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { ImageData, MAX_IMAGE_COUNT } from '../../../types/photoStudio';
import { processImage, rotateImage } from '../../../utils/imageProcessor';
import { generateNormalModeDocx, generateFileName } from '../../../utils/docxGenerator';
import { formatAutoCaption, stripPhotoPrefix } from '../../../utils/captionUtils';
import { Upload, X, Download, Image as ImageIcon, GripVertical, RotateCcw, RotateCw, ArrowRight, Sparkles } from 'lucide-react';

interface BulkModeProps {
  onSendToReport?: (photos: ImageData[]) => Promise<void>;
  reportId?: string;
}

export const BulkMode: React.FC<BulkModeProps> = ({ onSendToReport, reportId }) => {
  const [images, setImages] = useState<ImageData[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [isSending, setIsSending] = useState(false);

  const onDrop = async (acceptedFiles: File[]) => {
    if (images.length + acceptedFiles.length > MAX_IMAGE_COUNT) {
      alert(`Maximum ${MAX_IMAGE_COUNT} images allowed.`);
      return;
    }

    setIsProcessing(true);

    const newImagesPromises = acceptedFiles.map(async (file) => {
      try {
        const processed = await processImage(file);
        
        return {
          id: `${Date.now()}-${Math.random()}`,
          file,
          preview: processed.preview,
          description: '',
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

  const handleRemoveImage = (index: number) => {
    const newImages = [...images];
    if (newImages[index]?.preview) {
      URL.revokeObjectURL(newImages[index].preview);
    }
    newImages.splice(index, 1);
    setImages(newImages);
  };

  const handleDescriptionChange = (index: number, description: string) => {
    const newImages = [...images];
    newImages[index] = { ...newImages[index], description };
    setImages(newImages);
  };

  const handleRotate = async (index: number) => {
    const imageData = images[index];
    if (!imageData || !imageData.processedBlob) return;

    try {
      const currentRotation = imageData.rotationAngle || 0;
      const rotated = await rotateImage(imageData.processedBlob, currentRotation);

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

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (e: React.DragEvent, index: number) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === index) return;

    const newImages = [...images];
    const draggedImage = newImages[draggedIndex];
    newImages.splice(draggedIndex, 1);
    newImages.splice(index, 0, draggedImage);

    setImages(newImages);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const handleDownloadDocx = async () => {
    if (images.length === 0) {
      alert('Please upload at least one image before downloading.');
      return;
    }

    setIsGenerating(true);
    try {
      const fileName = generateFileName('Marine_Cargo_Report_Bulk');
      await generateNormalModeDocx(images, fileName);
    } catch (error: any) {
      console.error('Failed to generate DOCX:', error);
      alert(`Failed to generate document: ${error?.message || 'Unknown error'}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSendToReport = async () => {
    if (images.length === 0) {
      alert('No photos to send.');
      return;
    }
    if (!onSendToReport) return;

    setIsSending(true);
    try {
      await onSendToReport(images);
    } catch (err: any) {
      alert(`Failed to save to report: ${err?.message || err}`);
    } finally {
      setIsSending(false);
    }
  };

  const handleClearAll = () => {
    if (images.length === 0) return;
    if (confirm(`Remove all ${images.length} photos?`)) {
      images.forEach((img) => {
        if (img.preview) URL.revokeObjectURL(img.preview);
      });
      setImages([]);
    }
  };

  const handleAutoNumberCaptions = () => {
    if (images.length === 0) return;
    const renumbered = images.map((img, idx) => ({
      ...img,
      description: formatAutoCaption(img.description || '', idx, {
        keyword: 'Photo',
        startNum: 1,
      }),
    }));
    setImages(renumbered);
  };

  return (
    <div className="space-y-6">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-3 border-dashed rounded-2xl p-10 text-center transition-all cursor-pointer ${
          isDragActive
            ? 'border-indigo-600 bg-indigo-50/60 scale-[1.01]'
            : 'border-gray-300 hover:border-indigo-500 hover:bg-slate-50'
        }`}
      >
        <input {...getInputProps()} />
        <div className="flex flex-col items-center gap-3">
          <div className="p-4 bg-indigo-50 text-indigo-600 rounded-full">
            <Upload className="w-8 h-8" />
          </div>
          {isDragActive ? (
            <div>
              <p className="text-base font-bold text-indigo-700">Drop images here to batch import...</p>
              <p className="text-xs text-gray-500 mt-1">Release to start processing</p>
            </div>
          ) : (
            <div>
              <p className="text-base font-bold text-gray-800">
                Drag & Drop Images Here in Bulk
              </p>
              <p className="text-xs text-gray-500 mt-1">
                or click to browse files (Supports multiple JPG, PNG, BMP)
              </p>
            </div>
          )}
          {isProcessing && (
            <div className="flex items-center gap-2 text-indigo-600 mt-2">
              <div className="animate-spin rounded-full h-4 w-4 border-2 border-indigo-600 border-t-transparent"></div>
              <span className="text-xs font-semibold">Processing orientation & EXIF...</span>
            </div>
          )}
        </div>
      </div>

      {images.length > 0 && (
        <>
          {/* Summary & Actions Bar */}
          <div className="bg-slate-50 rounded-xl p-4 border border-slate-200 flex flex-wrap justify-between items-center gap-4">
            <div>
              <h3 className="text-sm font-bold text-gray-900">
                {images.length} {images.length === 1 ? 'Photo' : 'Photos'} In Queue
              </h3>
              <p className="text-xs text-gray-500">
                Drag cards to reorder sequence • Click × to remove
              </p>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleAutoNumberCaptions}
                className="px-3 py-1.5 text-xs text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg border border-indigo-200 transition font-semibold flex items-center gap-1.5 cursor-pointer shadow-2xs"
                title="Auto-number captions sequentially preserving existing text"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                <span>Auto-Number Captions</span>
              </button>

              <button
                type="button"
                onClick={handleClearAll}
                className="px-3 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded-lg border border-red-200 transition font-medium"
              >
                Clear Queue
              </button>

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
                {isGenerating ? 'Generating...' : 'Download DOCX'}
              </button>
            </div>
          </div>

          {/* Grid of photos */}
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
            {images.map((image, index) => (
              <div
                key={image.id}
                draggable
                onDragStart={() => handleDragStart(index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragEnd={handleDragEnd}
                className={`relative bg-white border rounded-xl overflow-hidden transition-all cursor-move hover:shadow-md group ${
                  draggedIndex === index
                    ? 'opacity-40 border-indigo-500'
                    : 'border-gray-200 hover:border-indigo-400'
                }`}
              >
                <div className="absolute top-2 left-2 bg-indigo-600 text-white text-[10px] font-bold px-2 py-0.5 rounded-full z-10 shadow-xs">
                  #{index + 1}
                </div>

                <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
                  {image.rotated && (
                    <button
                      type="button"
                      onClick={() => handleRotate(index)}
                      className="bg-blue-600 hover:bg-blue-700 text-white p-1 rounded-full shadow-xs transition-colors"
                      title="Rotate 90° anti-clockwise"
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

                <div className="absolute top-2 left-1/2 transform -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity z-10 pointer-events-none">
                  <div className="bg-slate-900/80 text-white p-1 rounded">
                    <GripVertical size={14} />
                  </div>
                </div>

                <div className="aspect-square relative bg-slate-50 flex items-center justify-center">
                  {image.preview ? (
                    <img
                      src={image.preview}
                      alt={`Photo ${index + 1}`}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <ImageIcon className="w-8 h-8 text-gray-300" />
                  )}
                </div>

                <div className="p-2 bg-white border-t border-gray-100 space-y-1">
                  <input
                    type="text"
                    value={image.description || ''}
                    onChange={(e) => handleDescriptionChange(index, e.target.value)}
                    placeholder="Caption / observation..."
                    className="w-full text-xs px-2 py-1 border border-gray-200 rounded focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                  />
                  <p className="text-[10px] text-gray-400 truncate" title={image.file.name}>
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

export default BulkMode;
