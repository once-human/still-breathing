import { ShirtStage } from "@/components/ShirtStage";
import { drafts } from "@/lib/live";

/** Every shirt page shares the stage at the top, so the 3D stays up from one shirt to the next. */
export default async function ShirtsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <ShirtStage hidden={await drafts()} />
      {children}
    </>
  );
}
