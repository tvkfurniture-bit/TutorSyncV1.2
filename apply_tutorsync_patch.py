#!/usr/bin/env python3
"""
Applies the TutorSync premium layer + bug fixes to your ORIGINAL files.
Put these 4 files in one folder:
  index.html, Code.gs, tutorsync-premium-layer.html, apply_tutorsync_patch.py
Run:  python3 apply_tutorsync_patch.py
Output: ./out/index.html and ./out/Code.gs  (originals are never modified)
"""
import os, re, sys

def read(p):
    with open(p, encoding='utf-8') as f: return f.read()

def write(p, s):
    os.makedirs('out', exist_ok=True)
    with open(os.path.join('out', p), 'w', encoding='utf-8', newline='\n') as f: f.write(s)

report = []
def ok(name, cond):
    report.append(('APPLIED ' if cond else 'SKIPPED ') + name)

# ---------------- index.html ----------------
html = read('index.html')
layer = read('tutorsync-premium-layer.html')

if 'id="ts-premium"' in html:
    ok('Premium layer (already present)', False)
else:
    assert '</head>' in html, 'index.html: </head> not found'
    html = html.replace('</head>', layer + '\n</head>', 1)
    ok('Premium layer inserted before </head>', True)

# Fix: admin tutor edit overwrote bio/languages/timing/availability with hard-coded values
a = "async function saveAdminTutor(e, tutorId) {"
if a in html and '_o=k=>' not in html:
    html = html.replace(a, a + "\n    const _o=k=>((state.adminCache.tutors||[]).find(x=>x.TutorId===tutorId)||{})[k]||'';", 1)
    n = 0
    for old, new in [
        ("availabilityDays: 'Mon, Tue, Wed, Thu, Fri, Sat'", "availabilityDays: parseArr(_o('AvailabilityDays')).join(', ')||'Mon, Tue, Wed, Thu, Fri, Sat'"),
        ("preferredTiming: 'Evening'", "preferredTiming: _o('PreferredTiming')||'Evening'"),
        ("languages: 'English'", "languages: parseArr(_o('Languages')).join(', ')||'English'"),
        ("shortBio: 'Verified Tutor'", "shortBio: _o('ShortBio')||'Verified Tutor'"),
    ]:
        if old in html: html = html.replace(old, new, 1); n += 1
    ok('Tutor edit no longer wipes bio/languages/timing/availability (%d/4)' % n, n == 4)
else:
    ok('Tutor edit data-loss fix', False)

# Fix: invalid unescaped & in the Gate-4 UPI deep link
old = '&pn=${encodeURIComponent(p.TutorName)}&am=${Number(p.NetPayoutAmount).toFixed(2)}&tn=${encodeURIComponent(p.PayoutId)}&cu=INR"'
new = '&amp;pn=${encodeURIComponent(p.TutorName)}&amp;am=${Number(p.NetPayoutAmount).toFixed(2)}&amp;tn=${encodeURIComponent(p.PayoutId)}&amp;cu=INR"'
ok('Escaped & in Gate-4 UPI link', old in html)
html = html.replace(old, new, 1)

write('index.html', html)

# ---------------- Code.gs ----------------
gs = read('Code.gs')

# Fix: duplicate trailing functions override the full versions (reviews lost on public profiles)
names = ['handlePublicGetLocalityDirectory_', 'handlePublicGetTutorProfile_', 'handlePublicGetRequirementCard_']
counts = {n: len(re.findall(r'function ' + n + r'\(', gs)) for n in names}
if all(c == 2 for c in counts.values()):
    cut = gs.rfind('function handlePublicGetLocalityDirectory_(')
    tail = gs[cut:]
    # sanity: the tail must contain only these three functions
    tail_fns = re.findall(r'^function (\w+)\(', tail, re.M)
    if sorted(tail_fns) == sorted(names):
        gs = gs[:cut].rstrip() + '\n'
        ok('Removed 3 duplicate trailing functions (restores approved reviews + verified flags)', True)
    else:
        ok('Duplicate-function removal (unexpected tail: %s)' % tail_fns, False)
else:
    ok('Duplicate-function removal (counts %s)' % counts, False)

# Fix: remove duplicated router lines (keep first occurrence)
removed = 0
for act in ['publicGetTutorProfile', 'publicGetRequirementCard', 'publicGetLocalityDirectory']:
    pat = re.compile(r"^[ \t]*if \(action === '%s'\) return \w+\(payload\);\r?\n" % act, re.M)
    ms = list(pat.finditer(gs))
    for m in reversed(ms[1:]):
        gs = gs[:m.start()] + gs[m.end():]; removed += 1
ok('Removed %d duplicate router lines' % removed, removed == 3)

# Fix: admin tutor edit blanked DocumentUrl when not supplied
pat = re.compile(r"DocumentUrl: cleanStr_\(p\.documentUrl, 400\),(\s*)UpiId:")
if pat.search(gs):
    gs = pat.sub(lambda m: "DocumentUrl: (p.documentUrl !== undefined ? cleanStr_(p.documentUrl, 400) : existing.DocumentUrl)," + m.group(1) + "UpiId:", gs, count=1)
    ok('Tutor edit preserves DocumentUrl', True)
else:
    ok('Tutor edit preserves DocumentUrl', False)

write('Code.gs', gs)

print('\n'.join(report))
print('\nDone. Review ./out/index.html and ./out/Code.gs, then deploy.')
if any(r.startswith('SKIPPED') for r in report):
    print('NOTE: a SKIPPED line means that spot did not match your file exactly; apply it by hand.')
