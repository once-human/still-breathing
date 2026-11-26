import { redirect } from "next/navigation";
import { adminReady, currentAdmin } from "@/lib/admin/auth";
import { LoginForm } from "./LoginForm";

export const dynamic = "force-dynamic";
export const metadata = { title: "sign in" };

export default async function AdminLogin() {
  if (await currentAdmin()) redirect("/admin");
  return (
    <div className="mx-auto grid min-h-dvh max-w-sm content-center gap-8 px-4">
      <div>
        <div className="text-[34px] font-extrabold tracking-[-0.04em]">sahn <span className="font-normal text-quiet">admin</span></div>
        <p className="mt-2 text-[13px] text-quiet">a one-time link goes to the admin&apos;s email. no password.</p>
      </div>
      {adminReady() ? <LoginForm /> : <p className="text-[13px] text-quiet">the admin isn&apos;t set up on this deployment yet.</p>}
    </div>
  );
}
