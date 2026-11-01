"""Extracts the collage material: creatures (several poses), heroes and
adventure-map objects for each wing, as .rgba files in OUT/<wing>/.

    extract_set.py H4ART.py ARCHIVE OUT [WING,WING...]"""
import importlib.util
import os
import random
import sys

spec = importlib.util.spec_from_file_location('h4art', sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
data, entries, order = m.read_index(sys.argv[2])
out = sys.argv[3]
names = [e['name'] for e in order]
low = {n.lower(): n for n in names}
rnd = random.Random(7)

WINGS = {
    'paradise': dict(
        creatures=['archangel', 'champion', 'crusader', 'monk', 'squire', 'griffin', 'unicorn',
                   'faerie dragon', 'phoenix', 'sprite', 'elf', 'white tiger', 'titan', 'mage', 'genie',
                   'dwarf', 'halfling', 'gold golem', 'wolf', 'waspwort', 'mermaid', 'leprechaun', 'satyr',
                   'peasant', 'pikeman', 'crossbowman', 'thunderbird', 'air elemental', 'water elemental',
                   'naga', 'centaur', 'earth elemental'],
        heroes=['life', 'order', 'nature'],
        objects=['adv_object.castle.haven', 'adv_object.castle.academy', 'adv_object.castle.preserve',
                 'adv_object.trees', 'adv_object.flowers', 'adv_object.shrines', 'adv_object.water falls',
                 'adv_object.farms', 'adv_object.animals', 'adv_object.creature generators',
                 'adv_object.moral-luck boosters', 'adv_object.shrubs', 'adv_object.mushrooms']),
    'hell': dict(
        creatures=['black dragon', 'bone dragon', 'vampire', 'ghost', 'mummy', 'skeleton', 'zombie',
                   'cerberus', 'archdevil', 'imp', 'venom spawn', 'medusa', 'minotaur', 'efreet',
                   'nightmare', 'beholder', 'hydra', 'troglodyte', 'orc', 'ogre mage', 'cyclops',
                   'behemoth', 'troll', 'harpy', 'berserker', 'bandit', 'ice demon', 'fire elemental',
                   'mantis', 'pirate', 'sea monster', 'gargoyle'],
        heroes=['death', 'chaos'],
        objects=['adv_object.castle.necropolis', 'adv_object.castle.asylum', 'adv_object.castle.stronghold',
                 'adv_object.burned out buildings', 'adv_object.skeletons', 'adv_object.lava flows-mud',
                 'adv_object.cracks-holes', 'adv_object.stumps', 'adv_object.rocks',
                 'adv_object.creature bank', 'adv_object.geysers', 'adv_object.mushrooms']),
}

# The faction wings (combat: the left one the player's, the right one the
# enemy's), each with the map objects of both looks (light and dark).
LIGHT_OBJECTS = ['adv_object.trees', 'adv_object.flowers', 'adv_object.shrines', 'adv_object.shrubs',
                 'adv_object.farms', 'adv_object.animals']
DARK_OBJECTS = ['adv_object.burned out buildings', 'adv_object.skeletons', 'adv_object.lava flows-mud',
                'adv_object.cracks-holes', 'adv_object.stumps', 'adv_object.rocks']
FACTIONS = {
    'life': (['pikeman', 'crossbowman', 'ballista', 'squire', 'monk', 'crusader', 'champion', 'archangel',
              'peasant', 'griffin'], 'haven'),
    'order': (['dwarf', 'halfling', 'gold golem', 'mage', 'naga', 'genie', 'titan', 'dragon golem',
               'peasant', 'gargoyle'], 'academy'),
    'nature': (['sprite', 'wolf', 'elf', 'white tiger', 'unicorn', 'griffin', 'faerie dragon', 'waspwort',
                'satyr', 'leprechaun', 'mermaid', 'phoenix'], 'preserve'),
    'death': (['skeleton', 'imp', 'cerberus', 'ghost', 'vampire', 'venom spawn', 'bone dragon', 'mummy',
               'zombie', 'archdevil'], 'necropolis'),
    'chaos': (['bandit', 'orc', 'medusa', 'minotaur', 'efreet', 'nightmare', 'black dragon', 'troglodyte',
               'beholder', 'hydra'], 'asylum'),
    'might': (['berserker', 'centaur', 'harpy', 'cyclops', 'nomad', 'ogre mage', 'thunderbird', 'behemoth',
               'troll', 'wolf'], 'stronghold'),
}
for f, (crea, town) in FACTIONS.items():
    WINGS[f] = dict(creatures=crea, heroes=[f],
                    objects=[f'adv_object.castle.{town}'] + LIGHT_OBJECTS + DARK_OBJECTS)
if len(sys.argv) > 4:  # only these wings
    WINGS = {k: v for k, v in WINGS.items() if k in sys.argv[4].split(',')}
ACTIONS = ['wait', 'melee', 'fidget', 'death', 'ranged', 'cast']
DIRS = ['se', 'sw', 'ne', 'nw', 'e', 'w']


def save(wing, tag, name, which=None):
    try:
        imgs = m.sprite_images(m.payload(data, entries, name))
    except Exception:
        return False
    full = [im for im in imgs if im[3] is not None and not im[0].lower().startswith('shadow')
            and im[1] in (0, 4) and (im[2][2] - im[2][0]) * (im[2][3] - im[2][1]) > 400]
    if not full:
        return False
    im = full[len(full) // 2 if which is None else min(which, len(full) - 1)]
    w, h = im[2][2] - im[2][0], im[2][3] - im[2][1]
    if sum(1 for i in range(3, len(im[3]), 4) if im[3][i]) < 300:
        return False
    d = os.path.join(out, wing)
    os.makedirs(d, exist_ok=True)
    m.write_rgba(os.path.join(d, f"{tag}.rgba"), w, h, im[3])
    return True


for wing, spec_ in WINGS.items():
    n = 0
    for c in spec_['creatures']:
        got = 0
        for act in ACTIONS:
            for dr in DIRS:
                nm = low.get(f"actor_sequence.{c}.combat.{act}.{dr}.h4d")
                if nm and rnd.random() < 0.6 and save(wing, f"c_{c.replace(' ', '_')}_{act}_{dr}", nm):
                    got += 1
                    n += 1
                if got >= 4:
                    break
            if got >= 4:
                break
    for faction in spec_['heroes']:
        cands = [x for x in names if x.lower().startswith(f"actor_sequence.hero.{faction}") and '.combat.' in x.lower()]
        rnd.shuffle(cands)
        for x in cands[:8]:
            if save(wing, 'h_' + x.split('.', 1)[1].replace(' ', '_').replace('.h4d', ''), x):
                n += 1
    for prefix in spec_['objects']:
        cands = [x for x in names if x.lower().startswith(prefix) and not entries[x.lower()]['alias']]
        rnd.shuffle(cands)
        limit = 6 if '.castle.' in prefix else 10
        for x in cands[:limit]:
            if save(wing, 'o_' + x.split('.', 1)[1].replace(' ', '_').replace('.h4d', ''), x, which=0):
                n += 1
    print(wing, n)
