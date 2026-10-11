export const MAX_IMAGE_BYTES = 2 * 1024 * 1024
// Long edge that keeps printed text legible for OCR while staying small on slow networks.
const MAX_EDGE = 1600

async function decode(file: Blob): Promise<ImageBitmap | HTMLImageElement> {
  if ('createImageBitmap' in window) {
    try {
      return await createImageBitmap(file, { imageOrientation: 'from-image' })
    } catch {
      // fall through to <img> decoding
    }
  }
  const url = URL.createObjectURL(file)
  try {
    const img = new Image()
    img.src = url
    await img.decode()
    return img
  } finally {
    URL.revokeObjectURL(url)
  }
}

function toJpeg(canvas: HTMLCanvasElement, quality: number): Promise<Blob | null> {
  return new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
}

/** Downscale and re-encode a photo as JPEG until it is under `maxBytes`. */
export async function compressImage(file: Blob, maxBytes = MAX_IMAGE_BYTES): Promise<Blob> {
  const source = await decode(file)
  let scale = Math.min(1, MAX_EDGE / Math.max(source.width, source.height))
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('canvas unavailable')

  for (let attempt = 0; attempt < 6; attempt++) {
    canvas.width = Math.max(1, Math.round(source.width * scale))
    canvas.height = Math.max(1, Math.round(source.height * scale))
    ctx.drawImage(source, 0, 0, canvas.width, canvas.height)
    for (const quality of [0.8, 0.6, 0.45]) {
      const blob = await toJpeg(canvas, quality)
      if (blob && blob.size <= maxBytes) return blob
    }
    scale *= 0.75
  }
  throw new Error('image too large')
}
