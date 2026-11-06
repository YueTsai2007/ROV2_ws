#!/usr/bin/env python3
"""Generate the 6 x 6 allocation matrix from the documented CAD geometry."""
from pathlib import Path
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]

def matrix(config):
    thrusters = config['thrusters']
    if set(thrusters) != {'thruster_%d' % i for i in range(6)}:
        raise ValueError('Expected exactly thruster_0 through thruster_5')
    columns = []
    for i in range(6):
        item = thrusters['thruster_%d' % i]
        r = np.asarray(item['origin'], dtype=float)
        d = np.asarray(item['direction'], dtype=float)
        if r.shape != (3,) or d.shape != (3,) or not np.isfinite(np.r_[r, d]).all():
            raise ValueError('Invalid geometry for thruster %d' % i)
        if not np.isclose(np.linalg.norm(d), 1.0, atol=1e-3):
            raise ValueError('Non-unit direction for thruster %d' % i)
        d = d / np.linalg.norm(d)
        columns.append(np.r_[d, np.cross(r, d)])
    raw = np.column_stack(columns)
    # CAD rounded one axis at a different precision; remove only numerically
    # zero singular values so the upstream pinv does not amplify roundoff.
    u, singular, vt = np.linalg.svd(raw, full_matrices=False)
    singular[singular < 1e-8] = 0.0
    return (u * singular) @ vt

def main():
    with (ROOT / 'config/thruster_manager.yaml').open() as f:
        config = yaml.safe_load(f)
    b = matrix(config)
    with (ROOT / 'config/TAM.yaml').open('w') as f:
        yaml.safe_dump({'tam': b.tolist()}, f, sort_keys=False)
    print('TAM shape:', b.shape, 'effective rank (tol=1e-8):', np.linalg.matrix_rank(b, tol=1e-8))
    print('Singular values:', np.linalg.svd(b, compute_uv=False))
    print(b)

if __name__ == '__main__':
    main()
