import hashes from "./asset-hashes.json";

const H = hashes as Record<string, string>;

/** the address to fetch a public file from: with its content hash, so a changed file is never served stale */
export const asset = (url: string) => {
  const h = H[url];
  return h ? `${url}?v=${h}` : url;
};
