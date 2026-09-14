import React, { useState } from 'react';
import { ImageData, MAX_IMAGE_COUNT, MIN_IMAGE_COUNT, ALLOWED_IMAGE_TYPES } from '../../../types/photoStudio';
import ImageUploadBox from './ImageUploadBox';
import { Download, CheckCircle2, ArrowRight, Sparkles } from 'lucide-react';
import { processImage, isValidImageType, rotateImage } from '../../../utils/imageProcessor';
import { generateNormalModeDocx, generateFileName } from '../../../utils/docxGenerator';
import { formatAutoCaption } from '../../../utils/captionUtils';

interface NormalModeProps {
  onSendToReport?: (photos: ImageData[]) => Promise<void>;
  reportId?: string;
}

export const NormalMode: React.FC<NormalModeProps> = ({ onSendToReport, reportId }) => {
  const [imageCount, setImageCount] = useState<string>('4');
  const [boxes, setBoxes] = useState<number>(0);
  const [images, setImages] = useState<(ImageData | null)[]>([]);
  const [error, setError] = useState<string>('');
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);

  const handleGenerateBoxes = () => {
    const count = parseInt(imageCount, 10);
    
    if (isNaN(count)) {
      setError('Please enter a valid number');
      return;
    }
    if (count < MIN_IMAGE_COUNT) {
      setError(`Minimum ${MIN_IMAGE_COUNT} image required`);
      return;
    }
    if (count > MAX_IMAGE_COUNT) {
      setError(`Maximum ${MAX_IMAGE_COUNT} images allowed`);
      return;
    }

    setError('');
    setBoxes(count);
    setImages(new Array(count).fill(null));
  };

  const handleImageUpload = async (index: number, file: File) => {
    if (!isValidImageType(file, ALLOWED_IMAGE_TYPES)) {
      setError('Invalid file type. Please upload JPG, PNG, or BMP images.');
      return;
    }

    setError('');

    try {
      const processed = await processImage(file);
      
      const newImageData: ImageData = {
        id: `${Date.now()}-${index}`,
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
      };

      const updatedImages = [...images];
      updatedImages[index] = newImageData;
      setImages(updatedImages);
    } catch (err: any) {
      setError(`Failed to process image: ${err?.message || 'Unknown error'}`);
      const updatedImages = [...images];
      updatedImages[index] = null;
      setImages(updatedImages);
    }
  };

  const handleDescriptionChange = (index: number, description: string) => {
    const updatedImages = [...images];
    if (updatedImages[index]) {
      updatedImages[index] = {
        ...updatedImages[index]!,
        description,
      };
      setImages(updatedImages);
    }
  };

  const handleClear = (index: number) => {
    const updatedImages = [...images];
    if (updatedImages[index]?.preview) {
      URL.revokeObjectURL(updatedImages[index]!.preview);
    }
    updatedImages[index] = null;
    setImages(updatedImages);
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

      const updatedImages = [...images];
      updatedImages[index] = {
        ...imageData,
        preview: rotated.preview,
        processedBlob: rotated.blob,
        dimensions: {
          width: rotated.width,
          height: rotated.height,
        },
        rotationAngle: rotated.rotation,
      };
      setImages(updatedImages);
    } catch (err) {
      console.error('Error rotating image:', err);
      alert('Failed to rotate image.');
    }
  };

  const handleAutoNumberCaptions = () => {
    const updated = images.map((img, idx) => {
      if (!img) return null;
      return {
        ...img,
        description: formatAutoCaption(img.description || '', idx, {
          keyword: 'Photo',
          startNum: 1,
        }),
      };
    });
    setImages(updated);
  };

  const handleDownloadDocx = async () => {
    const validImages = images.filter((img): img is ImageData => img !== null && !!img.processedBlob);
    if (validImages.length === 0) {
      alert('Please upload at least one image before downloading.');
      return;
    }

    setIsGenerating(true);
    try {
      const fileName = generateFileName('Marine_Cargo_Report_Normal');
      await generateNormalModeDocx(validImages, fileName);
    } catch (err: any) {
      alert(`Download failed: ${err?.message || err}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const handleSendToReport = async () => {
    const validImages = images.filter((img): img is ImageData => img !== null && !!img.file);
    if (validImages.length === 0) {
      alert('No uploaded photos to send.');
      return;
    }
    if (!onSendToReport) return;

    setIsSending(true);
    try {
      await onSendToReport(validImages);
    } catch (err: any) {
      alert(`Failed to save to report: ${err?.message || err}`);
    } finally {
      setIsSending(false);
    }
  };

  const validCount = images.filter((img) => img !== null).length;

  return (
    <div className="space-y-6">
      {/* Box generation setup */}
      {boxes === 0 ? (
        <div className="bg-slate-50 border border-slate-200 rounded-2xl p-8 text-center max-w-md mx-auto space-y-4">
          <h3 className="text-lg font-bold text-gray-800">
            How many photo slots do you need?
          </h3>
          <p className="text-xs text-gray-500">
            Enter the exact count of photos to prepare individual captioned cards.
          </p>
          <div className="flex gap-2 max-w-xs mx-auto">
            <input
              type="number"
              min={1}
              max={500}
              value={imageCount}
              onChange={(e) => setImageCount(e.target.value)}
              className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none"
              placeholder="e.g. 6"
            />
            <button
              type="button"
              onClick={handleGenerateBoxes}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-lg transition"
            >
              Set Slots
            </button>
          </div>
          {error && <p className="text-xs text-red-600 font-medium">{error}</p>}
        </div>
      ) : (
        <>
          {/* Header Action Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 p-4 bg-slate-50 rounded-xl border border-slate-200">
            <div className="flex items-center gap-3">
              <span className="text-sm font-bold text-gray-800">
                {boxes} Slots ({validCount} Filled)
              </span>
              <button
                type="button"
                onClick={() => {
                  setBoxes(0);
                  setImages([]);
                }}
                className="text-xs text-indigo-600 hover:text-indigo-800 font-medium"
              >
                Change Count
              </button>
            </div>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={handleAutoNumberCaptions}
                disabled={validCount === 0}
                className="px-3 py-2 text-xs text-indigo-700 bg-indigo-50 hover:bg-indigo-100 rounded-lg border border-indigo-200 transition font-semibold flex items-center gap-1.5 cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed shadow-2xs"
                title="Auto-number captions sequentially preserving existing text"
              >
                <Sparkles className="w-3.5 h-3.5 text-indigo-600" />
                <span>Auto-Number Captions</span>
              </button>

              {onSendToReport && reportId && (
                <button
                  type="button"
                  onClick={handleSendToReport}
                  disabled={isSending || validCount === 0}
                  className="px-3 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed shadow-xs"
                >
                  <ArrowRight className="w-3.5 h-3.5" />
                  {isSending ? 'Sending to Report...' : 'Attach to Active Report'}
                </button>
              )}

              <button
                type="button"
                onClick={handleDownloadDocx}
                disabled={isGenerating || validCount === 0}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition flex items-center gap-1.5 disabled:opacity-40 disabled:cursor-not-allowed shadow-xs"
              >
                <Download className="w-3.5 h-3.5" />
                {isGenerating ? 'Generating...' : 'Download DOCX'}
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-50 text-red-700 rounded-lg text-xs border border-red-200">
              {error}
            </div>
          )}

          {/* Grid of boxes */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {images.map((img, idx) => (
              <ImageUploadBox
                key={idx}
                index={idx}
                imageData={img}
                onImageUpload={handleImageUpload}
                onDescriptionChange={handleDescriptionChange}
                onClear={handleClear}
                onRotate={handleRotate}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default NormalMode;
