"""Merges translations into a catalog: set_uk.py <catalog.json> <batch.json>
where batch.json is {"<id>": "<uk>"}; checks every uk encodes in cp1251."""
import json
import sys

cat, batch = sys.argv[1], json.load(open(sys.argv[2]))
items = json.load(open(cat))
byid = {str(it['id']): it for it in items}
for k, v in batch.items():
    v.replace('’', "'").encode('cp1251')
    byid[k]['uk'] = v
json.dump(items, open(cat, 'w'), ensure_ascii=False, indent=1)
print(f'{len(batch)} set, {sum(1 for i in items if i["uk"])}/{len(items)} translated')
