/**
 * Facts about a page for search engines (schema.org, as JSON-LD): what the shop is, and on a shirt's page its price,
 * that it's made to order, free delivery and how long it takes. "<" is escaped so no text can close the script.
 */
export function JsonLd({ data }: { data: object }) {
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }} />;
}
