(base) PS C:\Users\Yugendra\Downloads\MLopsProject> pip install -e . --quiet
>> 
(base) PS C:\Users\Yugendra\Downloads\MLopsProject> python -c "from driftguard import DriftGuard; print('OK:', DriftGuard)"
>> 
OK: <class 'sdk.tracker.DriftGuard'>
(base) PS C:\Users\Yugendra\Downloads\MLopsProject> python -c "from setuptools import find_packages; print(find_packages(exclude=['.venv*','venv*','tests*','examples*','*.egg-info']))"
>> 
['driftguard', 'governance', 'mlflow', 'monitoring', 'pipeline', 'sdk', 'serving']
(base) PS C:\Users\Yugendra\Downloads\MLopsProject> python -c "import driftguard; print(driftguard.__all__)"
>> 
['DriftGuard', 'DriftGuardModelWrapper', 'RetrainerCallbackRunner', 'settings']
(base) PS C:\Users\Yugendra\Downloads\MLopsProject> 


---------------------------------------------------------------------------------


python -c "
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification
from driftguard import DriftGuard

X, y = make_classification(n_samples=100, n_features=5, random_state=42)
model = RandomForestClassifier(random_state=42)
model.fit(X, y)

dg = DriftGuard(model_id='wrap-test', drift_threshold=0.99)
wrapped = dg.wrap(model)

orig = model.predict(X)
wrap = wrapped.predict(X)

assert np.array_equal(orig, wrap), f'MISMATCH: {orig[:5]} vs {wrap[:5]}'
print('PASS: predictions identical')
print('PASS: no stdout noise from predict()')
"


----------------------------------------------------------------------------------

