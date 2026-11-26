export class ShopError extends Error {
  constructor(message: string, readonly status = 502) {
    super(message);
  }
}
