# 02 looking up

## The idea
The back looks down on the course; this one lies on the infield and looks up, east, at 10 pm on 8 December 2026, at
the real sky (positions computed in gen.py for Mahalaxmi, 18.98 N 72.82 E): Orion about 40 degrees up with his belt
and the dashed line the old way down to Sirius, low over the towers; Aldebaran and the bull's two horns above; Procyon;
Capella high in the north-east. Only stars a city sky shows. Two altitude circles as broken pale-blue arcs, the
figures in ring-blue dashes. Along the bottom, the towers east of the course (Lower Parel) and the course's rain trees,
leaning into a fish-eye bowl toward the zenith. Under them the name, **fred again..**, set along the horizon's curve,
and the chart's caption in ring blue: *8 dec, 10 pm*. The two altitude circles are named, 30° and 60°, at their ends. Continued from the first-round draft he liked
("just on the chest... looks kind of nice").

Changes from that draft: no stage roof; towers chosen so none stands under a bright star (each star has clear sky);
rain trees drawn as umbrella crowns of different sizes on short trunks, each a loose green screen with a paper gap
where it overlaps the next; one magnitude system (a four-ray cross for the first-magnitude stars, Sirius the longest;
plain dots in three sizes for the rest; the belt three equal stars; the Pleiades a knot of six); the arcs and pointer
break round every star; the wordmark and caption.

From the critic, not taken: making the left towers lean left (in a fish-eye looking up, verticals converge on the
zenith, so towers left of centre lean right; that is what the projection does); moving the 60° circle off Aldebaran
(Aldebaran really is at 60°; the circle breaks round it instead); the Hyades' V (drawn, then dropped: at 17 cm its
corners crowd Aldebaran into a knot of dots); the caption at 55% (Shantell under 8 mm loses its e's bar at print).

## Placement
Centre chest: 17 cm wide, top 11 cm under the high shoulder point.

## How it goes with the back
Same pen, same inks, same place, opposite direction: the back is the map from above, the front is the sky from the
ground. The rain trees are the course's own; the towers are the city the back hatches in plan.

## Honest weak spots
- The biggest and most illustrative front; it is restrained by having few marks, not by being small.
- The trees on short trunks are a simplification of a rain tree; up close they edge toward a children's-book tree.
- The caption is Shantell Sans at 8.4 mm, the smallest size at which its e keeps its crossbar through the 1 mm clean-up.

## Make it
`python3 gen.py` (print size: art.png and preview.png) or `R=1 python3 gen.py` (draft.png). Helpers in `../lib/`.
Inks: the back's own (black line #22201D, green #2F7D52, sea blue #6890C8, ring blue #2C46BE).
