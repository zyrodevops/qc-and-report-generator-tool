import {
  Document,
  Packer,
  Paragraph,
  Table,
  TableRow,
  TableCell,
  ImageRun,
  WidthType,
  AlignmentType,
  VerticalAlign,
  TextRun,
  BorderStyle,
} from 'docx';
import { ImageData, ProModeOptions } from '../types/photoStudio';

const FIXED_IMAGE_WIDTH = 285;
const FIXED_IMAGE_HEIGHT = 198;
const PRO_IMAGE_WIDTH = 310;
const PRO_IMAGE_HEIGHT = 210;

/**
 * Trigger file download in browser
 */
export function triggerBlobDownload(blob: Blob, fileName: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = fileName.endsWith('.docx') ? fileName : `${fileName}.docx`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

export async function generateNormalModeDocx(
  images: ImageData[],
  fileName: string = 'Marine_Cargo_Report'
): Promise<void> {
  try {
    const tableRows: TableRow[] = [];
    
    for (let i = 0; i < images.length; i += 2) {
      const leftImage = images[i];
      const rightImage = images[i + 1];
      
      const imageRow = await createImageRow(leftImage, rightImage);
      tableRows.push(imageRow);
      
      const descRow = createDescriptionRow(
        leftImage?.description || '',
        rightImage?.description || ''
      );
      tableRows.push(descRow);
    }
    
    const table = new Table({
      rows: tableRows,
      width: { size: 100, type: WidthType.PERCENTAGE },
      columnWidths: [5000, 5000],
      borders: {
        top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        left: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        insideHorizontal: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        insideVertical: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      },
    });
    
    const doc = new Document({
      sections: [{
        children: [table],
      }],
    });
    
    const blob = await Packer.toBlob(doc);
    triggerBlobDownload(blob, fileName);
  } catch (error) {
    console.error('DOCX generation failed:', error);
    throw error;
  }
}

async function createImageRow(left: ImageData, right: ImageData | null): Promise<TableRow> {
  const cells: TableCell[] = [];
  cells.push(await createImageCell(left));
  
  if (right) {
    cells.push(await createImageCell(right));
  } else {
    cells.push(createEmptyCell());
  }
  
  return new TableRow({ children: cells });
}

function createDescriptionRow(leftDesc: string, rightDesc: string): TableRow {
  const cells: TableCell[] = [
    createTextCell(leftDesc),
    createTextCell(rightDesc),
  ];
  return new TableRow({ children: cells });
}

async function createImageCell(imageData: ImageData): Promise<TableCell> {
  try {
    if (!imageData.processedBlob) {
      throw new Error('No processed blob');
    }
    
    const arrayBuffer = await imageData.processedBlob.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);
    
    const image = new ImageRun({
      data: uint8Array,
      transformation: {
        width: FIXED_IMAGE_WIDTH,
        height: FIXED_IMAGE_HEIGHT,
      },
    });
    
    return new TableCell({
      children: [
        new Paragraph({
          children: [image],
          alignment: AlignmentType.CENTER,
          spacing: {
            before: 5,
            after: 5,
          },
        }),
      ],
      width: { size: 50, type: WidthType.PERCENTAGE },
      verticalAlign: VerticalAlign.CENTER,
      margins: {
        top: 5,
        bottom: 5,
        left: 0,
        right: 0,
      },
    });
  } catch (error) {
    console.error('Image cell error:', error);
    return createEmptyCell();
  }
}

function createTextCell(text: string): TableCell {
  return new TableCell({
    children: [
      new Paragraph({
        children: [
          new TextRun({
            text: text || '',
            font: 'Arial',
            size: 22, // 11pt
            color: '000000',
          }),
        ],
        alignment: AlignmentType.CENTER,
        spacing: {
          before: 5,
          after: 5,
        },
      }),
    ],
    width: { size: 50, type: WidthType.PERCENTAGE },
    margins: {
      top: 5,
      bottom: 5,
      left: 20,
      right: 20,
    },
  });
}

function createEmptyCell(): TableCell {
  return new TableCell({
    children: [new Paragraph('')],
    width: { size: 50, type: WidthType.PERCENTAGE },
    margins: {
      top: 5,
      bottom: 5,
      left: 0,
      right: 0,
    },
  });
}

export function generateFileName(prefix: string = 'Marine_Cargo_Report'): string {
  const date = new Date();
  const timestamp = date.toISOString().split('T')[0].replace(/-/g, '');
  const time = date.toTimeString().split(' ')[0].replace(/:/g, '');
  return `${prefix}_${timestamp}_${time}`;
}

export async function generateProModeDocx(
  images: ImageData[],
  options: ProModeOptions,
  fileName: string = 'Marine_Cargo_Report_Pro'
): Promise<void> {
  try {
    const tableRows: TableRow[] = [];
    
    if (options.addBorder && !options.showDescription) {
      // 2-column grid layout without descriptions
      for (let i = 0; i < images.length; i += 2) {
        const leftImage = images[i];
        const rightImage = images[i + 1];
        
        const imageRow = await createProImageRow(leftImage, rightImage, options);
        tableRows.push(imageRow);
      }
    } else {
      // Layout with descriptions
      for (let i = 0; i < images.length; i += 2) {
        const leftImage = images[i];
        const rightImage = images[i + 1];
        
        const imageRow = await createProImageRow(leftImage, rightImage, options);
        tableRows.push(imageRow);
        
        const descRow = createProDescriptionRow(
          leftImage?.description || '',
          rightImage?.description || '',
          options,
          !!rightImage
        );
        tableRows.push(descRow);
      }
    }
    
    const table = new Table({
      rows: tableRows,
      width: { size: 100, type: WidthType.PERCENTAGE },
      columnWidths: [5000, 5000],
      borders: {
        top: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        bottom: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        left: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        right: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        insideHorizontal: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
        insideVertical: { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' },
      },
    });
    
    const doc = new Document({
      sections: [{
        children: [table],
      }],
    });
    
    const blob = await Packer.toBlob(doc);
    triggerBlobDownload(blob, fileName);
  } catch (error) {
    console.error('Pro DOCX generation failed:', error);
    throw error;
  }
}

async function createProImageRow(
  left: ImageData,
  right: ImageData | null,
  options: ProModeOptions
): Promise<TableRow> {
  const cells: TableCell[] = [];
  cells.push(await createProImageCell(left, options));
  
  if (right) {
    cells.push(await createProImageCell(right, options));
  } else {
    cells.push(createProEmptyCell(options));
  }
  
  return new TableRow({ children: cells });
}

function createProDescriptionRow(
  leftDesc: string,
  rightDesc: string,
  options: ProModeOptions,
  hasRightImage: boolean = true
): TableRow {
  const cells: TableCell[] = [
    createProTextCell(leftDesc, options),
  ];
  
  if (hasRightImage) {
    cells.push(createProTextCell(rightDesc, options));
  } else {
    cells.push(createProEmptyCell(options));
  }
  
  return new TableRow({ children: cells });
}

async function createProImageCell(
  imageData: ImageData,
  options: ProModeOptions
): Promise<TableCell> {
  try {
    if (!imageData.processedBlob) {
      throw new Error('No processed blob');
    }
    
    const arrayBuffer = await imageData.processedBlob.arrayBuffer();
    const uint8Array = new Uint8Array(arrayBuffer);
    
    const image = new ImageRun({
      data: uint8Array,
      transformation: {
        width: PRO_IMAGE_WIDTH,
        height: PRO_IMAGE_HEIGHT,
      },
    });
    
    const cellBorders = options.addBorder
      ? {
          top: { style: BorderStyle.SINGLE, size: 12, color: options.boxColor },
          bottom: { style: BorderStyle.SINGLE, size: 12, color: options.boxColor },
          left: { style: BorderStyle.SINGLE, size: 12, color: options.boxColor },
          right: { style: BorderStyle.SINGLE, size: 12, color: options.boxColor },
        }
      : undefined;
    
    return new TableCell({
      children: [
        new Paragraph({
          children: [image],
          alignment: AlignmentType.CENTER,
          spacing: {
            before: options.addBorder ? 10 : 5,
            after: options.addBorder ? 10 : 5,
          },
        }),
      ],
      width: { size: 50, type: WidthType.PERCENTAGE },
      verticalAlign: VerticalAlign.CENTER,
      borders: cellBorders,
      margins: {
        top: options.addBorder ? 10 : 5,
        bottom: options.addBorder ? 10 : 5,
        left: options.addBorder ? 10 : 20,
        right: options.addBorder ? 10 : 20,
      },
    });
  } catch (error) {
    console.error('Image cell error:', error);
    return createProEmptyCell(options);
  }
}

function createProTextCell(text: string, options: ProModeOptions): TableCell {
  const cellBorders = options.addBorder
    ? {
        top: { style: BorderStyle.SINGLE, size: 12, color: options.boxColor },
        bottom: { style: BorderStyle.SINGLE, size: 12, color: options.boxColor },
        left: { style: BorderStyle.SINGLE, size: 12, color: options.boxColor },
        right: { style: BorderStyle.SINGLE, size: 12, color: options.boxColor },
      }
    : undefined;

  return new TableCell({
    children: [
      new Paragraph({
        children: [
          new TextRun({
            text: text || '',
            font: options.fontType,
            size: options.fontSize * 2,
            color: options.fontColor,
          }),
        ],
        alignment: AlignmentType.CENTER,
        spacing: {
          before: 5,
          after: 5,
        },
      }),
    ],
    width: { size: 50, type: WidthType.PERCENTAGE },
    borders: cellBorders,
    margins: {
      top: 5,
      bottom: 5,
      left: 20,
      right: 20,
    },
  });
}

function createProEmptyCell(options: ProModeOptions): TableCell {
  return new TableCell({
    children: [new Paragraph('')],
    width: { size: 50, type: WidthType.PERCENTAGE },
    margins: {
      top: 5,
      bottom: 5,
      left: 0,
      right: 0,
    },
  });
}

