// What the site says while something loads: a word in hand under the breathing dot, picked at random for each
// load from that load's own list (never the same word twice in a row), so waiting reads as part of the night.

const W = {
  /** the tee on its own, on the paper */
  tee: [
    "dressing it..", "ironing it out..", "steaming the cotton..", "folding it open..", "pinning it up..",
    "smoothing the hem..", "shaking it out..", "finding the collar..", "hanging it straight..", "airing it out..",
    "snipping the tags..", "checking the stitches..", "warming the cotton..", "out of the bag..", "pressing the seams..",
    "straightening the sleeves..", "picking off the lint..", "squaring the shoulders..", "letting it breathe..",
    "fresh off the rail..", "unfolding..", "one more steam..",
  ],
  /** someone wearing it */
  worn: [
    "getting dressed..", "pulling it over..", "sleeves on..", "fixing the collar..", "one last mirror check..",
    "wristband on..", "the queue's moving..", "finding the gang..", "texting the group chat..", "the auto's here..",
    "phone at 100%..", "doors at 6..", "ticket on screen..", "stretching the legs..", "drinking water..",
    "tying the laces..", "walking in..", "finding a spot near the front..", "shoulders loose..", "outfit check..",
    "ready in five..", "deep breath..",
  ],
  /** on the table: the tee laid flat, from above */
  close: [
    "closer..", "leaning in..", "laying it flat..", "on the table..", "smoothing it out..", "nose to the print..",
    "counting the threads..", "reading the small print..", "finding the details..", "under the lamp..", "every line..",
    "squinting..", "magnifying glass out..", "the fine print..", "close enough to smell it..", "tracing the ink..",
    "macro mode..", "look closer..", "into the weave..", "palms flat..", "hold still..",
  ],
  /** another shirt */
  shirt: [
    "next shirt..", "swapping shirts..", "off the rail..", "another one..", "trying this one..", "quick change..",
    "outfit change..", "back to the rail..", "the other one..", "one more..", "how about this one..",
    "off the hanger..", "switching it up..", "wardrobe change..", "hold on, this one..", "next look..",
    "spin the rack..", "same night, new shirt..", "change of plans..", "this one instead..", "tags on..",
  ],
  /** the light: the studio */
  studio: [
    "lights up..", "softboxes on..", "rolling out the paper..", "moving the key light..", "bouncing the light..",
    "quiet on set..", "metering..", "white balance..", "fill light..", "diffusing..", "flash charging..",
    "dialling it in..", "clean light..", "setting up the stands..", "light check..", "killing the spill..",
    "the shoot's on..", "fan off..", "taping the marks..", "one more test frame..",
  ],
  /** the light: by the window */
  window: [
    "curtains open..", "sun through the glass..", "morning light..", "golden hour..", "blinds up..",
    "dust in the light..", "window seat..", "a slow sunday..", "letting the light in..", "soft daylight..",
    "chai by the window..", "the shadow of the frame..", "lazy light..", "the room warms up..",
    "watching the light move..", "opening the window..", "light on the floor..", "quiet afternoon..",
    "the pigeons are out..", "sun on the sill..",
  ],
  /** the light: at the show */
  show: [
    "lights down..", "doors open..", "the crowd's in..", "bass check..", "haze machine on..", "lasers warming up..",
    "soundcheck..", "the drop is coming..", "phones up..", "strobes ready..", "bpm rising..", "find your people..",
    "the room goes dark..", "here we go..", "stage lights..", "the build..", "hands up soon..",
    "the speakers are humming..", "the intro..", "someone's crying already..", "front row..",
  ],
  /** making a photo */
  photo: [
    "developing..", "in the darkroom..", "fixing the print..", "shaking the polaroid..", "drying the film..",
    "exposing..", "pulling focus..", "printing..", "dodge and burn..", "the chemicals..", "wait for it..",
    "red light on..", "rinsing..", "hanging it to dry..", "almost a photo..", "say cheese..", "the shutter's open..",
    "light leaks..", "rewinding..", "one more second in the tray..",
  ],
  /** the fit: bodies and sizes */
  fit: [
    "measuring..", "tape out..", "chest, then length..", "finding your size..", "the tailor's tape..",
    "s, m, l, hmm..", "checking the shoulders..", "the fitting room..", "pins in mouth..", "how's the drop..",
    "length check..", "sleeve check..", "standing straight..", "the mirror..", "arms up..", "turn around..",
    "loose or snug..", "trying on sizes..", "your size, coming..", "a little room to move..",
  ],
} as const;

export type WordKind = keyof typeof W;
const last: Partial<Record<WordKind, string>> = {};

/** a word for this load, never the one the same kind of load showed last */
export function word(kind: WordKind): string {
  const list: readonly string[] = W[kind];
  let w = list[Math.floor(Math.random() * list.length)];
  if (w === last[kind] && list.length > 1) w = list[(list.indexOf(w) + 1) % list.length];
  last[kind] = w;
  return w;
}
