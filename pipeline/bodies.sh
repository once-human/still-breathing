#!/bin/bash
# The five fit-mode bodies, from Indian adult anthropometry (height cm, chest/bust girth cm):
#   m163 a slim 5'4" man, m170 the median man, m177 a tall broad man, f155 a petite woman, f162 the median woman.
cd "$(dirname "$0")"; mkdir -p bodies
for spec in "m163 163 86 m" "m170 170 94 m" "m177 177 104 m" "f155 155 84 f" "f162 162 92 f"; do
  set -- $spec
  nice -n 15 blender -b --factory-startup -P body.py -- "$PWD/bodies/$1.blend" $2 $3 $4 2>&1 | grep -E "iter|saved|Error"
done
# The two people who wear the shop tee (the poster stills and the 3D view): an athletic Indian man and woman, lean
# and muscled (muscle and weight held, height fitted): ma175 175 cm, fa163 163 cm
nice -n 15 blender -b --factory-startup -P body.py -- "$PWD/bodies/ma175.blend" 175 0 m 1.0 0.4 2>&1 | grep -E "saved|Error"
nice -n 15 blender -b --factory-startup -P body.py -- "$PWD/bodies/fa163.blend" 163 0 f 0.8 0.65 2>&1 | grep -E "saved|Error"
