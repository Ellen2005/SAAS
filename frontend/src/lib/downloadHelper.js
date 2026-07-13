import { API_URL } from './api';

export async function downloadBlob(url, filename) {
  try {
    const response = await fetch(`${API_URL}${url}`);
    if (!response.ok) throw new Error(`Download failed: ${response.status}`);
    const blob = await response.blob();
    const blobUrl = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(blobUrl);
    a.remove();
  } catch (err) {
    console.error('Download failed:', err);
    throw err;
  }
}
