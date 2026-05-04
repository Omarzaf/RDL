import json
from common import PROCESSED_DIR
(PROCESSED_DIR/'revolving_vectors.json').write_text(json.dumps([],indent=2))
(PROCESSED_DIR/'yearly_currents.json').write_text(json.dumps([{'year':y,'dx':0,'dy':0,'count':0} for y in range(2018,2026)],indent=2))
print('Saved revolving door vectors')
