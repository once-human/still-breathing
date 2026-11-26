import { Confirm } from "./Confirm";

export const dynamic = "force-dynamic";
export const metadata = { title: "sign in", referrer: "no-referrer" as const };

/** The email link lands here with its token after the #, so it never reaches a server log; the button sends it. */
export default function AdminConfirm() {
  return (
    <div className="mx-auto grid min-h-dvh max-w-sm content-center gap-8 px-4">
      <div className="text-[34px] font-extrabold tracking-[-0.04em]">sahn <span className="font-normal text-quiet">admin</span></div>
      <Confirm />
    </div>
  );
}
