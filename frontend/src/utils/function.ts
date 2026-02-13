export function normalizeImageUrl(url: string): string {
  try {
    const urlObj = new URL(url);
    if (urlObj.hostname === "localhost" || urlObj.hostname === "127.0.0.1") {
      return urlObj.pathname + urlObj.search;
    }
    return url;
  } catch {
    return url.startsWith("/") ? url : `/${url}`;
  }
}
