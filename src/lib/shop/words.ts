import type { EventKind, Stage } from "./orders";

/** How the order pages say things: stages, timeline steps, dates and times in India's time. */
export const STAGE_WORD: Record<Stage, string> = {
  paying: "not paid",
  paid: "paid",
  printing: "being made",
  shipped: "on its way",
  out: "out for delivery",
  delivered: "delivered",
  attention: "held up, we're on it",
  cancelled: "cancelled",
};

export const EVENT_WORD: Record<EventKind, string> = {
  placed: "order placed",
  paid: "paid",
  address: "address changed",
  printing: "sent to print",
  partner: "update from the workshop",
  shipped: "left with the courier",
  out: "out for delivery",
  delivered: "delivered",
  trouble: "held up",
  cancelled: "cancelled",
  refunded: "refunded",
  admin: "by sahn",
  note: "note",
};

const IST = "Asia/Kolkata";
export const day = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", timeZone: IST }).toLowerCase();
export const dayYear = (iso: string) => new Date(iso).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: IST }).toLowerCase();
export const time = (iso: string) => new Date(iso).toLocaleTimeString("en-IN", { hour: "numeric", minute: "2-digit", timeZone: IST }).toLowerCase();
export const when = (iso: string) => `${day(iso)}, ${time(iso)}`;
