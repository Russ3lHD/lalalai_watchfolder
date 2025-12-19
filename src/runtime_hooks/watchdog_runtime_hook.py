# Runtime hook to check availability of watchdog and its platform backends
# Writes a small JSON file `watchdog_runtime_check.json` next to the current working directory

import json
import os
import time

results = {
    'timestamp': time.time(),
    'watchdog_present': False,
    'submodules': {},
    'observer_instantiable': False,
}

try:
    import watchdog
    results['watchdog_present'] = True

    submods = [
        'observers.winapi',
        'observers.read_directory_changes',
        'observers.polling',
        'observers.inotify',
        'observers.fsevents',
        'events',
        'utils',
    ]

    for sm in submods:
        try:
            __import__('watchdog.' + sm)
            results['submodules'][sm] = True
        except Exception:
            results['submodules'][sm] = False

    # Check if we can instantiate the default Observer
    try:
        from watchdog.observers import Observer
        o = Observer()
        results['observer_instantiable'] = hasattr(o, 'start')
        # don't start the observer here
    except Exception:
        results['observer_instantiable'] = False

except Exception as e:
    results['error'] = str(e)

# Try to write results to a JSON file in cwd so user can retrieve it when reporting issues
try:
    out_file = os.path.join(os.getcwd(), 'watchdog_runtime_check.json')
    with open(out_file, 'w') as f:
        json.dump(results, f, indent=2)
except Exception:
    # Best-effort, don't raise
    pass
