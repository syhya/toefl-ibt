"""Rebuild the private UI logo from the supplied Pack screenshot, without new art."""
from pathlib import Path
import hashlib
import json


def build(root, materials):
    import pymupdf
    root = Path(root)
    material = next((m for m in materials if m.get('kind') == 'pdf' and m.get('name') == '2026新托福Pack-1.pdf'), None)
    if not material:
        return {'status': 'reference-not-installed'}
    source = (root / 'data' / material['path']).resolve()
    if not source.is_relative_to((root / 'data').resolve()) or hashlib.sha256(source.read_bytes()).hexdigest() != material['sha256']:
        raise ValueError('The original exam UI reference changed; re-verify the source screenshot.')
    target = root / 'generated/assets/ui'
    target.mkdir(parents=True, exist_ok=True)
    bounds = (49.0, 50.0, 140.0, 75.0)
    with pymupdf.open(source) as document:
        document[2].get_pixmap(matrix=pymupdf.Matrix(4, 4), clip=pymupdf.Rect(bounds)).save(target / 'toefl-logo.png')
    report = {'sourcePath': material['path'], 'sourceSha256': material['sha256'],
              'physicalPage': 3, 'clipBoundsPdfPoints': bounds,
              'outputSha256': hashlib.sha256((target / 'toefl-logo.png').read_bytes()).hexdigest()}
    (target / 'source.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    catalog = json.loads((root / 'generated/catalog.json').read_text())
    print(json.dumps(build(root, catalog['materials']), ensure_ascii=False, indent=2))
