import { PUBLIC_API_BASE_URL } from '$env/static/public';

export const apiBaseUrl = PUBLIC_API_BASE_URL.replace(/\/$/, '');
