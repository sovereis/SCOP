"""Create a public allowlist. Workspace, Python code and docs are never copied."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parent

def build(output=None):
    destination = Path(output) if output else ROOT / 'public'
    if destination.resolve() in (ROOT, ROOT.parent):
        raise ValueError('Output must be a dedicated build directory')
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for name in ('index.html', 'style.css', 'app.js', 'assets/hero.webp'):
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, target)

if __name__ == '__main__':
    build()
