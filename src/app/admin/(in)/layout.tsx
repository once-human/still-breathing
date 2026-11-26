import { requireAdmin } from "@/lib/admin/auth";
import { CsrfProvider, Nav } from "../ui/client";

/** Signed in only. Each page below checks the session again itself; this one draws the frame. */
export default async function InLayout({ children }: { children: React.ReactNode }) {
  const a = await requireAdmin();
  return (
    <CsrfProvider token={a.csrf}>
      <div className="md:flex">
        <Nav email={a.email} />
        <div className="min-w-0 flex-1 px-4 pb-24 pt-6 md:px-10 md:pt-10">{children}</div>
      </div>
    </CsrfProvider>
  );
}
