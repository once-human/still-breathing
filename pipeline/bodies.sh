#!/bin/bash
# The five fit-mode bodies, from Indian adult anthropometry (height cm, chest/bust girth cm):
#   m163 a slim 5'4" man, m170 the median man, m177 a tall broad man, f155 a petite woman, f162 the median woman.
cd "$(dirname "$0")"; mkdir -p bodies
for spec in "m163 163 86 m" "m170 170 94 m" "m177 177 104 m" "f155 155 84 f" "f162 162 92 f"; do
  set -- $spec
  nice -n 15 blender -b --factory-startup -P body.py -- "$PWD/bodies/$1.blend" $2 $3 $4 2>&1 | grep -E "iter|saved|Error"
done
