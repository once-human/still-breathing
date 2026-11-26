import "server-only";
import { exec, rows } from "./db";

export type Note = { id: number; order_id: string; at: string; who: string; text: string };
export type AuditRow = { id: number; at: string; who: string; action: string; target: string | null; detail: Record<string, unknown> | null; ip: string | null };

/** notes on an order (or on a customer, with target "customer:<email>") */
export const notesFor = (target: string) => rows<Note>("SELECT * FROM admin_notes WHERE order_id = $1 ORDER BY at", [target]);
export const addNote = (target: string, who: string, text: string) => exec("INSERT INTO admin_notes (order_id, who, text) VALUES ($1, $2, $3)", [target, who, text]);
export const auditFor = (target: string) => rows<AuditRow>("SELECT * FROM admin_audit WHERE target = $1 ORDER BY at", [target]);

export async function auditPage(opts: { q?: string; before?: number; limit?: number }) {
  const limit = Math.min(200, opts.limit ?? 100);
  const params: (string | number)[] = [];
  const where: string[] = [];
  const p = (v: string | number) => {
    params.push(v);
    return "$" + params.length;
  };
  if (opts.q) {
    const n = p(`%${opts.q}%`);
    where.push(`(action ILIKE ${n} OR target ILIKE ${n} OR who ILIKE ${n} OR detail::text ILIKE ${n})`);
  }
  if (opts.before) where.push(`id < ${p(opts.before)}`);
  const lim = p(limit);
  return rows<AuditRow>(`SELECT * FROM admin_audit ${where.length ? "WHERE " + where.join(" AND ") : ""} ORDER BY id DESC LIMIT ${lim}`, params);
}
