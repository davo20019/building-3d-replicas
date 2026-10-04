"""Release a new version: raise it everywhere, check, record it, tag and push.
  python3 tools/release.py patch|minor|major|X.Y.Z "What changed, one line"   [--no-push]

Claude Code and Codex keep users on the version in the plugin manifests until it changes, so a push without
a new version reaches nobody who installed the plugin. This script writes the new version into every file
that carries it (VERSION_FILES), adds the notes to CHANGELOG.md, runs the checks, commits, tags vX.Y.Z and
pushes. It stops before committing if any check fails, leaving the edits for you to inspect.

Checks: the fast tests, the Agent Skills validator (skills-ref, via uvx) and `claude plugin validate`
when the claude CLI is installed.
"""
import datetime, json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'building-3d-replicas'
SEMVER = re.compile(r'^\d+\.\d+\.\d+$')

# (file, pattern with one group around the version, how to write a new one)
VERSION_FILES = [
    (ROOT / '.claude-plugin' / 'plugin.json', r'"version": "([^"]+)"', '"version": "{v}"'),
    (ROOT / '.codex-plugin' / 'plugin.json', r'"version": "([^"]+)"', '"version": "{v}"'),
    (SKILL / 'SKILL.md', r'^  version: "([^"]+)"', '  version: "{v}"'),
    (SKILL / 'pyproject.toml', r'^version = "([^"]+)"', 'version = "{v}"'),
]
README = ROOT / 'README.md'
CHANGELOG = ROOT / 'CHANGELOG.md'

def current_versions():
    found = {}
    for path, pattern, _ in VERSION_FILES:
        m = re.search(pattern, path.read_text(), re.M)
        if not m:
            sys.exit(f'release: no version found in {path.relative_to(ROOT)}')
        found[path.relative_to(ROOT).as_posix()] = m.group(1)
    return found

def bumped(version, part):
    if SEMVER.match(part):
        return part
    major, minor, patch = map(int, version.split('.'))
    if part == 'major':
        return f'{major + 1}.0.0'
    if part == 'minor':
        return f'{major}.{minor + 1}.0'
    if part == 'patch':
        return f'{major}.{minor}.{patch + 1}'
    sys.exit(f'release: "{part}" is not patch, minor, major or X.Y.Z')

def run(cmd, **kw):
    print('$', ' '.join(cmd), flush=True)
    r = subprocess.run(cmd, cwd=ROOT, **kw)
    if r.returncode:
        sys.exit(f'release: failed: {" ".join(cmd)} (edits left in place, nothing committed)')

def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    push = '--no-push' not in sys.argv
    if len(args) != 2 or not args[1].strip():
        sys.exit(__doc__)
    part, notes = args
    if subprocess.run(['git', 'status', '--porcelain'], cwd=ROOT, capture_output=True, text=True).stdout.strip():
        sys.exit('release: commit or stash your changes first; a release should contain only the version bump')

    versions = current_versions()
    old = max(versions.values(), key=lambda v: tuple(map(int, v.split('.'))))
    new = bumped(old, part)
    if tuple(map(int, new.split('.'))) <= tuple(map(int, old.split('.'))):
        sys.exit(f'release: {new} is not newer than {old}')
    if len(set(versions.values())) > 1:
        print(f'release: versions disagreed ({versions}); all become {new}')

    for path, pattern, template in VERSION_FILES:
        text = path.read_text()
        path.write_text(re.sub(pattern, template.format(v=new), text, count=1, flags=re.M))
    major_minor = '.'.join(new.split('.')[:2])
    README.write_text(re.sub(r'^## Status: early \([\d.]+\)', f'## Status: early ({major_minor})', README.read_text(), flags=re.M))
    log = CHANGELOG.read_text() if CHANGELOG.exists() else '# Changelog\n'
    head, _, rest = log.partition('\n')
    CHANGELOG.write_text(f'{head}\n\n## {new} ({datetime.date.today().isoformat()})\n\n- {notes.strip()}\n{rest}')

    run(['uv', 'run', '-q', '--project', str(SKILL), 'pytest', '-q', 'tests', '-m', 'not slow'])
    run(['uvx', '--from', 'git+https://github.com/agentskills/agentskills#subdirectory=skills-ref',
         'skills-ref', 'validate', str(SKILL)])
    if shutil.which('claude'):
        run(['claude', 'plugin', 'validate', '.'])
    else:
        print('release: claude CLI not found, skipping claude plugin validate')

    run(['git', 'add', '-A'])
    run(['git', 'commit', '-q', '-m', f'Release {new}: {notes.strip()}'])
    run(['git', 'tag', '-a', f'v{new}', '-m', f'{new}: {notes.strip()}'])
    if push:
        run(['git', 'push', '-q', 'origin', 'HEAD', f'v{new}'])
        print(f'release: {new} pushed. Claude Code users get it with `claude plugin update '
              f'building-3d-replicas@building-3d-replicas`; Codex users with `codex plugin marketplace upgrade`.')
    else:
        print(f'release: {new} committed and tagged locally; push with: git push origin HEAD v{new}')

if __name__ == '__main__':
    main()
