#!/bin/bash
# presentation stills, then transparent web turntables, for both colourways
cd "$(dirname "$0")"
P=~/Documents/Projects/fred-again-india-tee/previews; T=~/Documents/Projects/tryon-site/public/tee
for c in black cream; do for v in front q back; do
  nice -n 15 blender -b tee-drape.blend -P render.py -- B $c $v $P/3d-B-$c-$v.png 96 > /tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/batch.log 2>&1 && echo "still $c $v"
done; done
for c in black cream; do mkdir -p $T/fred-b-$c/turntable; for a in 0 30 60 90 120 150 180 210 240 270 300 330; do
  W=880 H=1120 TRANSPARENT=1 nice -n 15 blender -b tee-drape.blend -P render.py -- B $c a$a $T/fred-b-$c/turntable/a$a.png 64 > /tmp/claude-1000/-home-onkar-Documents/a4dfe67b-0718-408b-8186-b5f2b378874d/scratchpad/batch.log 2>&1 && echo "turn $c $a"
done; done
echo ALL DONE
