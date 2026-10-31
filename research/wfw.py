import json,numpy as np,pandas as pd
from sklearn.linear_model import Ridge
from wf import NEW,target
P=pd.read_pickle('panel.pkl');o={}
for Y in range(1996,2027):
    tr=P[P.index<pd.Timestamp(f'{Y}-01-01')-pd.Timedelta(days=35)]
    m=Ridge(alpha=50).fit(tr[NEW].to_numpy(),target(tr,'xs').to_numpy());p=m.predict(tr[NEW].to_numpy())
    o[str(Y)]={'w':list(map(float,m.coef_)),'b':float(p.mean()-m.intercept_),'k':float(tr.old.std()/p.std())}
json.dump(o,open('wf_weights.json','w'))
print(len(o))
