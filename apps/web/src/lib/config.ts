import { browser } from '$app/environment';
import { PUBLIC_API_BASE_URL } from '$env/static/public';

const LOCAL_API_BASE_URL = 'http://127.0.0.1:8000';

function normalize(value: string): string {
  return value.trim().replace(/\/$/, '');
}

export function getApiBaseUrl(): string {
  if (PUBLIC_API_BASE_URL) {
    return normalize(PUBLIC_API_BASE_URL);
  }
  if (browser) {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return LOCAL_API_BASE_URL;
    }
  }
  return '';
}
