# Render Cached Build Patch (Python)

This patch adds a cached build step for Render to save minutes by reusing pip cache
and skipping dependency reinstall if `requirements.txt` hasn't changed.

## Quick Install
1. Copy `scripts/build_render.sh` into your repo.
2. Make sure it is executable (Render does not require this, but good locally):
   ```bash
   chmod +x scripts/build_render.sh
   ```
3. Edit your `render.yaml` service and replace its `buildCommand` with:
   ```yaml
   buildCommand: |
     chmod +x scripts/build_render.sh
     ./scripts/build_render.sh
   ```
   (Keep your existing `startCommand` and `healthCheckPath` lines.)

4. (Recommended) Add to `.gitignore` so cache artifacts aren't committed:
   ```gitignore
   .pip-cache/
   .render-requirements.hash
   ```

5. Commit & push, then Deploy in Render.

## Force Reinstall (if you change Python version or want a clean build)
```bash
rm -rf .pip-cache
rm -f .render-requirements.hash
```

## Multiple Services
If you have more than one `service` in `render.yaml`, use the same `buildCommand`
for each Python service.

## Example `render.yaml` snippet
```yaml
services:
  - type: web
    name: satpambot
    env: python
    buildCommand: |
      chmod +x scripts/build_render.sh
      ./scripts/build_render.sh
    startCommand: python main.py
    healthCheckPath: /healthz
    autoDeploy: false  # optional: avoid rebuild on every push
    envVars:
      - key: PYTHON_VERSION
        value: 3.11
```
