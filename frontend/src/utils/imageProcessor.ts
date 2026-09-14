import loadImage from 'blueimp-load-image';

export interface ProcessedImageResult {
  blob: Blob;
  preview: string;
  width: number;
  height: number;
  wasRotated: boolean;
  originalOrientation: 'portrait' | 'landscape';
}

/**
 * Decode, EXIF-correct, optionally rotate portrait→landscape, and optionally compress.
 *
 * @param file         The raw File from the user
 * @param compress     Whether to apply compression (default false = original bytes)
 * @param maxDimension Max px for both axes — only used when compress=true (default 1100)
 * @param quality      JPEG quality 0–1 — only used when compress=true (default 0.72)
 */
export async function processImage(
  file: File,
  compress: boolean = false,
  maxDimension: number = 1100,
  quality: number = 0.72
): Promise<ProcessedImageResult> {
  // ── No-compression path ───────────────────────────────────────────────────
  // Load via blueimp to resolve EXIF orientation, then write from the corrected
  // canvas at maximum quality so the DOCX always gets a correctly-oriented image.
  if (!compress) {
    return new Promise((resolve, reject) => {
      loadImage(
        file,
        (img) => {
          if (img instanceof Event) {
            reject(new Error('Failed to load image'));
            return;
          }
          const canvas = img as HTMLCanvasElement;
          const width = canvas.width;
          const height = canvas.height;
          const originalOrientation = width < height ? 'portrait' : 'landscape';

          // Determine output MIME type — preserve PNG losslessly, JPEG at q=1.0
          const mimeType = file.type === 'image/png' ? 'image/png' : 'image/jpeg';
          const outQuality = file.type === 'image/png' ? undefined : 1.0;

          if (height > width) {
            // Portrait → rotate to landscape (requires canvas)
            const rotatedCanvas = document.createElement('canvas');
            rotatedCanvas.width = height;
            rotatedCanvas.height = width;
            const rotatedCtx = rotatedCanvas.getContext('2d');
            if (!rotatedCtx) { reject(new Error('Failed to create rotation canvas')); return; }

            rotatedCtx.translate(height / 2, width / 2);
            rotatedCtx.rotate((-90 * Math.PI) / 180);
            rotatedCtx.drawImage(canvas, -width / 2, -height / 2);

            rotatedCanvas.toBlob((blob) => {
              if (!blob) { reject(new Error('Failed to create rotated blob')); return; }
              resolve({
                blob,
                preview: URL.createObjectURL(blob),
                width: rotatedCanvas.width,
                height: rotatedCanvas.height,
                wasRotated: true,
                originalOrientation,
              });
            }, mimeType, outQuality);
          } else {
            // Landscape → write from EXIF-corrected canvas at max quality
            canvas.toBlob((blob) => {
              if (!blob) { reject(new Error('Failed to create blob')); return; }
              resolve({
                blob,
                preview: URL.createObjectURL(blob),
                width: canvas.width,
                height: canvas.height,
                wasRotated: false,
                originalOrientation,
              });
            }, mimeType, outQuality);
          }
        },
        { maxWidth: 32767, maxHeight: 32767, canvas: true, orientation: true }
      );
    });
  }

  // ── Compression path ─────────────────────────────────────────────────────
  return new Promise((resolve, reject) => {
    loadImage(
      file,
      async (img) => {
        if (img instanceof Event) {
          reject(new Error('Failed to load image'));
          return;
        }

        const canvas = img as HTMLCanvasElement;
        const ctx = canvas.getContext('2d');
        
        if (!ctx) {
          reject(new Error('Failed to get canvas context'));
          return;
        }

        const width = canvas.width;
        const height = canvas.height;
        const originalOrientation = width < height ? 'portrait' : 'landscape';

        if (height > width) {
          // Portrait → rotate to landscape
          const rotatedCanvas = document.createElement('canvas');
          rotatedCanvas.width = height;
          rotatedCanvas.height = width;
          const rotatedCtx = rotatedCanvas.getContext('2d');

          if (!rotatedCtx) {
            reject(new Error('Failed to create rotation canvas'));
            return;
          }

          rotatedCtx.translate(height / 2, width / 2);
          rotatedCtx.rotate((-90 * Math.PI) / 180);
          rotatedCtx.drawImage(canvas, -width / 2, -height / 2);

          rotatedCanvas.toBlob(
            (blob) => {
              if (!blob) {
                reject(new Error('Failed to create blob from rotated canvas'));
                return;
              }

              const preview = URL.createObjectURL(blob);
              resolve({
                blob,
                preview,
                width: rotatedCanvas.width,
                height: rotatedCanvas.height,
                wasRotated: true,
                originalOrientation,
              });
            },
            'image/jpeg',
            quality
          );
        } else {
          canvas.toBlob(
            (blob) => {
              if (!blob) {
                reject(new Error('Failed to create blob from canvas'));
                return;
              }

              const preview = URL.createObjectURL(blob);
              resolve({
                blob,
                preview,
                width: canvas.width,
                height: canvas.height,
                wasRotated: false,
                originalOrientation,
              });
            },
            'image/jpeg',
            quality
          );
        }
      },
      {
        maxWidth: maxDimension,
        maxHeight: maxDimension,
        canvas: true,
        orientation: true,
      }
    );
  });
}

export function isValidImageType(file: File, allowedTypes: string[]): boolean {
  return allowedTypes.includes(file.type);
}

export function getFileSizeDisplay(bytes: number): string {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
}

/**
 * Check if image is portrait orientation
 */
export function isPortraitImage(width: number, height: number): boolean {
  return height > width;
}

/**
 * Create a thumbnail preview
 */
export async function createThumbnail(
  file: File,
  maxWidth: number = 400,
  maxHeight: number = 400
): Promise<string> {
  return new Promise((resolve, reject) => {
    loadImage(
      file,
      (img) => {
        if (img instanceof Event) {
          reject(new Error('Failed to load thumbnail'));
          return;
        }

        const canvas = img as HTMLCanvasElement;
        resolve(canvas.toDataURL('image/jpeg', 0.7));
      },
      {
        maxWidth,
        maxHeight,
        canvas: true,
        orientation: true,
      }
    );
  });
}

/**
 * Rotate an image 90° anti-clockwise, re-encoding at the given quality.
 */
export async function rotateImage(
  blob: Blob,
  currentRotation: number = 0,
  quality: number = 0.72
): Promise<{ blob: Blob; preview: string; width: number; height: number; rotation: number }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(blob);

    img.onload = () => {
      URL.revokeObjectURL(url);

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');

      if (!ctx) {
        reject(new Error('Failed to get canvas context'));
        return;
      }

      // Swap width and height for 90-degree rotation
      canvas.width = img.height;
      canvas.height = img.width;

      // Rotate anti-clockwise by 90 degrees
      ctx.translate(canvas.width / 2, canvas.height / 2);
      ctx.rotate((-90 * Math.PI) / 180);
      ctx.drawImage(img, -img.width / 2, -img.height / 2);

      canvas.toBlob(
        (rotatedBlob) => {
          if (!rotatedBlob) {
            reject(new Error('Failed to create rotated blob'));
            return;
          }

          const preview = URL.createObjectURL(rotatedBlob);
          const newRotation = (currentRotation + 90) % 360;

          resolve({
            blob: rotatedBlob,
            preview,
            width: canvas.width,
            height: canvas.height,
            rotation: newRotation,
          });
        },
        'image/jpeg',
        quality
      );
    };

    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Failed to load image for rotation'));
    };

    img.src = url;
  });
}

