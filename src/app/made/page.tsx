import type { Metadata } from "next";
import Link from "next/link";
import { Label } from "@/components/Label";
import { BigWord } from "@/components/BigWord";
import pkg from "../../../package.json";

export const metadata: Metadata = {
  title: "how it's made · still breathing",
  description: "How a still breathing shirt is drawn, cut, simulated and shown: hand-made art from real places, a pattern graded on Indian bodies, cloth physics, and a path tracer that runs in your browser.",
};

type Part = { no: string; title: string; note?: string; body: string[]; facts?: [string, string][] };

const PARTS: Part[] = [
  {
    no: "01", title: "the drawings", note: "made, not generated",
    body: [
      "every back starts as a program that draws like a hand: a brush stroke whose pressure rises and falls along a slightly wandering path, lines that overshoot their corners, passes drawn twice where a pen would go back over them.",
      "the inks are drawn as separate layers, like an old hand-pulled print, and nudged a fraction of a millimetre out of register. the wobble, the uneven stipple and the misregistration are in the structure of the drawing, never a filter laid on top.",
      "an artist and a critic go round after round: render, look at it next to the last shirt, say what looks computer-made, fix it, render again. nothing ships until it holds up at full size.",
    ],
    facts: [["canvas", "3600 × 4800 px, hard edges only"], ["inks", "three plus one blue accent"], ["smallest mark", "about 0.6 mm"]],
  },
  {
    no: "02", title: "the places", note: "real geometry",
    body: [
      "the maps are drawn from openstreetmap: every building, road, lake and rail line is where it really is, then redrawn by hand in ink. the mumbai map is the race course by the sea; the bengaluru map is the city of lakes and the green line running out to the show at its last stop.",
      "the crowds are the crowds at each ground: the horizon you'd actually see from the field, the cold of a december night in bengaluru, the people you stand next to.",
    ],
  },
  {
    no: "03", title: "the lettering", note: "set by hand",
    body: [
      "the city, the dates and the small notes are set in figma, on the art, by eye: placed where the drawing leaves room, turned a few degrees, roughened so they sit in the same ink as everything else. each front is its own, on the left chest: again.. in four scripts (english, hindi, marathi and kannada), a seal, a map key, a wristband.",
    ],
  },
  {
    no: "04", title: "the shirt", note: "cut from the size chart",
    body: [
      "the tee in the viewer is not a model of a tee. it is cut from the same size chart as the one we send you, xs to 2xl, sewn panel by panel in a cloth simulation and dropped onto a body: dropped shoulder, straight boxy body, 2 cm rib collar, double-stitched hems.",
      "the cloth is heavy 240 gsm combed cotton jersey, simulated as such, so it makes a few big soft folds instead of many small wrinkles. the colours are measured from the real fabric, and the print sits at its real size and place on the back.",
    ],
    facts: [["cloth", "240 gsm, 100% combed cotton"], ["fit", "oversized, drop shoulder"], ["sizes", "xs, s, m, l, xl, 2xl"]],
  },
  {
    no: "05", title: "the bodies", note: "indian, measured",
    body: [
      "fit is shown on five indian bodies, women and men from 155 to 177 cm, built from indian sizing data rather than a western mannequin. each size is simulated on each body standing, with arms up at the show, and sitting, so the numbers you see (room at the chest, where the hem lands, where the sleeve ends) come from the cloth, not a table.",
    ],
  },
  {
    no: "06", title: "the viewer", note: "in your browser",
    body: [
      "the tee you turn is drawn live with webgpu, the newest graphics layer in browsers, at your screen's full sharpness and refresh rate. it turns by itself; put your pointer on it and it eases to a stop and is yours.",
      "the cloth moves for real. a net of about fourteen hundred points rides on the shirt: only the collar and the tops of the shoulders sit on the form, the yoke gives a little, the hem and sleeves hang free and trail a turn, and a slow breeze with gusts and lulls moves through it. nothing is painted on: the light follows the shape the cloth actually has that frame, so a ripple catches it the way moving cotton would.",
      "when it comes to rest, your browser path-traces the exact view in the background: real light from real-sized softboxes, bouncing between the folds, through the same cotton and ink as the offline renders. it works in thin strips so it never takes a frame from you, and it only fades in once it's clean.",
    ],
    facts: [["live view", "webgpu, falls back to webgl2"], ["path tracer", "written for this site, denoised"], ["photos", "the same tracer, story or post size"]],
  },
  {
    no: "07", title: "your privacy", note: "nothing leaves",
    body: [
      "the try-on reads your camera with a pose model that runs on your own device. the video is never recorded and never sent anywhere; close it and the camera is off.",
      "the countdown and weather show the city of the shirt you're looking at. for the generic parts of the page we guess your nearest show from a rough, city-level location of your connection: no permission prompt, nothing stored, nothing shared.",
    ],
  },
];

export default function Made() {
  return (
    <>
      <nav aria-label="Main" className="fixed inset-x-0 top-0 z-50 grid grid-cols-4 gap-3 bg-paper px-4 pt-3 pb-2 text-[13px] sm:gap-4 sm:text-[15px] md:grid-cols-7 lg:grid-cols-9">
        <Link href="/" className="truncate border-t border-line pt-1.5 font-semibold">still breathing</Link>
        <span className="hidden truncate border-t border-line pt-1.5 text-quiet lg:block">lineup 01</span>
        <span className="truncate border-t border-line pt-1.5">how it&apos;s made</span>
        <Link href="/#studio" className="truncate border-t border-line pt-1.5 text-quiet hover:text-ink">the tee</Link>
      </nav>
      <main className="pt-20">
        <BigWord word="how it's made" as="h1" className="px-4 text-[13vw] md:text-[10vw]" />
        <p className="mt-6 max-w-[56ch] px-4 text-[15px] text-ink/85">
          a shirt for a night you were there. here is everything between the idea and the tee on your back, minus the parts that are ours to keep.
        </p>
        <div className="mt-20 space-y-20 px-4">
          {PARTS.map((p) => (
            <section key={p.no} className="grid grid-cols-1 gap-x-4 md:grid-cols-12">
              <div className="md:col-span-7 lg:col-span-6 lg:col-start-2">
                <Label note={p.note}><span className="mr-3 text-quiet tnum">{p.no}</span>{p.title}</Label>
                <div className="space-y-4 text-[15px] leading-relaxed text-ink/85">
                  {p.body.map((b) => <p key={b.slice(0, 24)} className="max-w-[62ch]">{b}</p>)}
                </div>
              </div>
              {p.facts ? (
                <dl className="mt-8 space-y-2 self-start text-[14px] md:col-span-5 md:mt-[3.25rem] lg:col-span-4 lg:col-start-9">
                  {p.facts.map(([k, v]) => (
                    <div key={k} className="grid grid-cols-[7rem_1fr] gap-3 border-t border-line pt-1.5"><dt className="text-quiet">{k}</dt><dd>{v}</dd></div>
                  ))}
                </dl>
              ) : null}
            </section>
          ))}
        </div>
        <div className="mt-24 px-4">
          <Link href="/#studio" className="text-[clamp(28px,5vw,64px)] font-extrabold tracking-[-0.04em] hover:text-blue">see the tee →</Link>
        </div>
      </main>
      <footer className="mt-32 grid grid-cols-2 gap-3 px-4 pb-4 text-[13px] md:grid-cols-4">
        <span className="border-t border-line pt-1.5">still breathing, lineup 01</span>
        <span className="border-t border-line pt-1.5 text-quiet">made to order</span>
        <span className="hidden border-t border-line pt-1.5 text-quiet md:block">made in india</span>
        <span className="hidden border-t border-line pt-1.5 text-right text-quiet md:block">v{pkg.version}</span>
      </footer>
    </>
  );
}
