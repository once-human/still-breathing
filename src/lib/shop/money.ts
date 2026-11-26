/** money as the page writes it: ₹1,499, with Indian digit grouping, no paise when there are none */
export const rupees = (amount: number | string) => {
  const n = typeof amount === "string" ? Number(amount) : amount;
  if (!Number.isFinite(n)) return "";
  return "₹" + n.toLocaleString("en-IN", { minimumFractionDigits: Number.isInteger(n) ? 0 : 2, maximumFractionDigits: 2 });
};
