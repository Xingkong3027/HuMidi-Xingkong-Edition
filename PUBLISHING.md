# Publishing HuMidi: Xingkong Edition

This checklist assumes the GitHub fork has been renamed to
`Xingkong3027/HuMidi-Xingkong-Edition`.

## 1. Clone the fork and configure upstream

```powershell
git clone https://github.com/Xingkong3027/HuMidi-Xingkong-Edition.git
cd HuMidi-Xingkong-Edition
git remote add upstream https://github.com/smyGitt/HuMidi-Roblox-Piano-Autoplayer.git
git remote -v
```

`origin` must point to the Xingkong repository and `upstream` to the original
HuMidi repository.

## 2. Import this source tree

Copy the contents of this package into the cloned repository. Preserve the
clone's `.git` directory. Do not commit `.venv`, `build`, `dist`, caches, local
MIDI files, playlists, or saved user configuration.

Create a release branch:

```powershell
git switch -c release/xingkong-2.0.0-xk.1
```

## 3. Test locally

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m compileall -q .
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py
```

Complete the relevant items in `MANUAL_TEST_CHECKLIST.md`, including a real
Windows and Roblox input smoke test.

## 4. Commit and merge

```powershell
git status
git diff
git add -A
git diff --cached --check
git commit -m "feat: add HuMidi Xingkong Edition 2.0.0-xk.1"
git push -u origin release/xingkong-2.0.0-xk.1
```

Open a pull request from the release branch into `main`. Confirm that both CI
jobs pass, review the changed files, and then merge the pull request.

## 5. Create the release tag

The tag without its leading `v` must exactly match `APP_VERSION` in `main.py`.

```powershell
git switch main
git pull --ff-only origin main
git tag -a v2.0.0-xk.1 -m "HuMidi Xingkong Edition v2.0.0-xk.1"
git push origin v2.0.0-xk.1
```

Pushing the tag starts `.github/workflows/release.yml`. It runs tests, builds
Windows and macOS packages, creates SHA-256 checksums, and publishes a GitHub
prerelease. The workflow-dispatch option can rebuild only an existing tag.

## 6. Review the generated prerelease

Verify that the Release contains:

- `HuMidi-Xingkong-Edition.exe`;
- `HuMidi-Xingkong-Edition-Windows.zip` with license notices;
- the macOS tar and DMG packages;
- `SHA256SUMS.txt`;
- attribution and license files;
- GitHub-generated source archives.

Download the generated Windows package on a clean Windows machine, verify its
SHA-256 checksum, and repeat the manual smoke tests. Keep the first release
marked as a prerelease until target-system tests are complete.

## 7. Future upstream synchronization

Do not use GitHub's automatic “Sync fork” button without reviewing conflicts;
this edition intentionally changes the product name, configuration directory,
updater, UI, and release workflow.

```powershell
git fetch upstream
git switch -c sync/upstream-review
git merge upstream/main
```

Resolve and test the merge in the review branch before merging it into `main`.

