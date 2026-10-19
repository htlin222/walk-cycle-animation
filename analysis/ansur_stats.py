"""Side-view body landmarks from ANSUR II (US Army anthropometric survey, 4,082 men).

Download ANSUR_II_MALE_Public.csv from https://www.openlab.psu.edu/ansur2/ and pass its path.
Prints each dimension in mm and as a fraction of stature; the page converts these to leg-length units
(leg L = hip joint → ankle = trochanterion − lateral malleolus ≈ 828 mm ≈ 0.47 H; see proportions.py).
"""
import csv, json, statistics as st, sys, pathlib
rows = list(csv.DictReader(open(sys.argv[1], encoding='latin-1')))
want = ['stature', 'cervicaleheight', 'suprasternaleheight', 'acromialheight', 'chestheight', 'waistheightomphalion',
        'trochanterionheight', 'lateralmalleolusheight', 'chestdepth', 'waistdepth', 'buttockdepth',
        'neckcircumference', 'neckcircumferencebase', 'headlength', 'tragiontopofhead', 'acromionradialelength',
        'radialestylionlength', 'handlength', 'wristheight', 'crotchheight', 'bicepscircumferenceflexed',
        'forearmcircumferenceflexed', 'wristcircumference', 'thighcircumference', 'calfcircumference']
M = {w: st.mean(float(r[w]) for r in rows) for w in want}
for w in want: print(f"{w:28s} {M[w]:7.1f} mm  {M[w] / M['stature']:.3f} H")
json.dump(M, open(pathlib.Path(__file__).parent / 'data' / 'ansur2_male_means.json', 'w'), indent=1)
