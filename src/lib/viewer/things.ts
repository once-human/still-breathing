// What the wind brings over the table, and how each kind moves. Only things that look real up close: the leaves are
// scans of real dried leaves (oak, beech, hornbeam, dogwood, maple); the rest are drawn from their own structure
// (a loose cotton thread, a hair), the few that hold up next to a scan.
// Sizes in metres. In real units: grip is the friction against the surface (how hard the air must push, as a
// fraction of its weight, before it slides); drag how much the air's push accelerates it (1/m: the push is drag x
// the air's speed past it, squared); fall the speed it falls at in still air (m/s); lift how much a fast flow under
// it lifts it (1/m); catch scales its drag; spin, tumble how much it turns; curl how cupped it has dried (0 flat).

export type Kind = {
  atlas: "leaf" | "bits";
  cells: number[];
  size: [number, number];
  move: "slide" | "flutter" | "float" | "creep";
  grip: [number, number];
  lift: number; drag: number; fall: number; catch: number;
  spin: number; tumble: number; curl: number;
  soft?: boolean;
  tints?: [number, number, number][];
  weight: number;
};

/** each leaf cell's width in the atlas, cm (the scan's real size) */
export const LEAF_CELLS = [10.16, 10.16, 10.16, 10.16, 8.13, 8.13, 8.13, 8.63, 8.63, 8.63, 8.63, 7.11, 7.11, 7.11, 9.14, 9.14];

export const KINDS: Kind[] = [
  // dry oak leaves: stiff and cupped, they slide and scrape more than fly
  { atlas: "leaf", cells: [0, 1, 2, 3], size: [0, 0], move: "slide", grip: [0.34, 0.48], lift: 9, drag: 8, fall: 1.3, catch: 1, spin: 1, tumble: 0.8, curl: 0.15, weight: 3 },
  // beech and hornbeam: thinner, they lift on a puff and skate
  { atlas: "leaf", cells: [4, 5, 6, 7, 8, 9, 10], size: [0, 0], move: "slide", grip: [0.3, 0.44], lift: 11, drag: 10, fall: 1.05, catch: 1, spin: 1.1, tumble: 1, curl: 0.12, weight: 3 },
  // dogwood and maple: light, they flutter in and turn over
  { atlas: "leaf", cells: [11, 12, 13, 14, 15], size: [0, 0], move: "flutter", grip: [0.26, 0.4], lift: 14, drag: 13, fall: 0.8, catch: 1, spin: 1.3, tumble: 1.3, curl: 0.1, weight: 3 },
  // a loose thread: creeps along the surface, hardly ever leaves it
  { atlas: "bits", cells: [4], size: [0.045, 0.085], move: "creep", grip: [0.3, 0.5], lift: 4, drag: 7, fall: 0.7, catch: 1, spin: 0.7, tumble: 0.15, curl: 0, tints: [[0.12, 0.12, 0.13], [0.3, 0.36, 0.52], [0.62, 0.2, 0.18], [0.36, 0.3, 0.22]], weight: 1 },
  // a hair
  { atlas: "bits", cells: [5], size: [0.06, 0.1], move: "creep", grip: [0.32, 0.52], lift: 3, drag: 6, fall: 0.9, catch: 1, spin: 0.6, tumble: 0.1, curl: 0, tints: [[0.09, 0.07, 0.06], [0.2, 0.14, 0.1]], weight: 0.8 },
];
