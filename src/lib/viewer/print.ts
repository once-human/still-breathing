// Where the prints sit on the garment's texture (the pattern atlas: front panel left, back panel right,
// 110 x 86 cm each, at the same place for every size). The prints are their own textures at print resolution;
// these rectangles map the garment's UVs onto them. Must match pipeline/texture.py.
export type Rect = [u0: number, v0: number, du: number, dv: number];
const AW = 8800, AH = 3440;     // atlas at 40 px/cm
/** back: 13.5 x 18 in (34.3 x 45.7 cm), the largest the print partner prints at the art's 3:4, its top 9.5 cm
 *  under the high shoulder point */
export const PRINT_BACK: Rect = [5914 / AW, 540 / AH, 1372 / AW, 1829 / AH];
/** front: a 30 x 50 cm area across the front, its top 8 cm under the high shoulder point. Each shirt's front
 *  texture holds its own front in its own place there (pipeline/fronts.py) */
export const PRINT_FRONT: Rect = [1600 / AW, 480 / AH, 1200 / AW, 2000 / AH];

export const printBackURL = (d: string, t: string, full = false) => `/tee/fit/tex/print-back-${d}-${t}${full ? "-full" : ""}.webp`;
export const printFrontURL = (d: string, t: string) => `/tee/fit/tex/print-front-${d}-${t}.webp`;
