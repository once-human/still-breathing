import { ShirtStage } from "@/components/ShirtStage";

/** Every shirt page shares the stage at the top, so the 3D stays up from one shirt to the next. */
export default function ShirtsLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <ShirtStage />
      {children}
    </>
  );
}
