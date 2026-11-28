import { redirect } from "next/navigation";
import { adminReady, currentAdmin } from "@/lib/admin/auth";
import { LoginForm } from "./LoginForm";

export const dynamic = "force-dynamic";
export const metadata = { title: "sign in" };

export default async function AdminLogin() {
  if (await currentAdmin()) redirect("/admin");
  return (
    <div className="mx-auto grid min-h-dvh max-w-sm content-center gap-10 px-4">
      <div>
        <div className="text-[clamp(40px,10vw,54px)] font-extrabold leading-[0.95] tracking-[-0.045em]">sahn <span className="font-normal text-quiet">admin</span></div>
        <p className="mt-3 text-[15px] text-quiet">put in the site key once. this browser stays signed in while you keep using it, and 30 days away signs it out.</p>
      </div>
      {adminReady() ? <LoginForm /> : <p className="rounded-[14px] bg-s1 p-5 text-[15px] text-quiet">the admin isn&apos;t set up on this deployment yet.</p>}
    </div>
  );
}
