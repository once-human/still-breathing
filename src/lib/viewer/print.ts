// Where the prints sit on the garment's texture (the pattern atlas: front panel left, back panel right,
// 110 x 86 cm each, at the same place for every size). The prints are their own textures at print resolution;
// these rectangles map the garment's UVs onto them. Must match pipeline/texture.py.
export type Rect = [u0: number, v0: number, du: number, dv: number];
const AW = 8800, AH = 3440;     // atlas at 40 px/cm
/** back: 38.1 x 50.8 cm, its top 9.5 cm under the high shoulder point */
export const PRINT_BACK: Rect = [5838 / AW, 540 / AH, 1524 / AW, 2032 / AH];
/** chest: again.. in four scripts, 10.5 cm wide, on the wearer's left */
export const PRINT_FRONT: Rect = [2360 / AW, 760 / AH, 420 / AW, 648 / AH];

export const printBackURL = (d: string, t: string, full = false) => `/tee/fit/tex/print-back-${d}-${t}${full ? "-full" : ""}.webp`;
export const printFrontURL = (t: string) => `/tee/fit/tex/print-front-${t}.webp`;
