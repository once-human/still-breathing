import { requireAdmin } from "@/lib/admin/auth";
import { getSettings } from "@/lib/admin/settings";
import { Group, Page, Row, Section } from "../../ui/ui";
import { WordsForm } from "../settings/Fields";

export const metadata = { title: "site words" };
export const dynamic = "force-dynamic";

/** site words: the bits of the site's own text that are yours to change without a push */
export default async function Words() {
  await requireAdmin();
  const s = await getSettings(true);
  return (
    <>
      <Page title="site words" sub="changes show on the site within a minute, no push needed" />
      <Section title="on every page">
        <WordsForm initial={s} />
      </Section>
      <Section title="elsewhere">
        <Group>
          <Row icon="shirt" title="each shirt's name and words" sub="on its own page under shirts" href="/admin/products" />
          <Row icon="note" title="policies, delivery times and the rest" sub="in the code (src/content), because those pages are built ahead" muted />
        </Group>
      </Section>
    </>
  );
}
