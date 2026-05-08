# n8n JSON Handler — Error Log & Architecture Notes

## The Bug: `SyntaxError: Unexpected token r in JSON at position 1`

### Where the error originates
naskio's `PythonFunction.node.ts` parses the **entire stderr** of the spawned process as JSON:

```typescript
// PythonFunction.node.ts (simplified)
child.on('close', code => {
    if (!code) {
        returnData.items = JSON.parse(returnData.stderr);  // ← result channel is STDERR
    } else {
        returnData.error = new Error(returnData.stderr);
    }
});
```

The matching Python template writes the result to stderr:

```python
# script.template.py (naskio)
sys.stderr.write(json.dumps(new_items))
exit(0)
```

**Any content appearing on stderr before the JSON result breaks JSON.parse.**

---

## naskio PythonFunction Channel Architecture

| Channel  | naskio's use                                      | What scripts should do           |
|----------|---------------------------------------------------|----------------------------------|
| `stdin`  | Never written — input comes from a temp JSON file | Inner sub-subprocess reads stdin |
| `stdout` | Collected for `sendMessageToUI` (UI only)         | Write JSON result here (inner)   |
| `stderr` | `JSON.parse(stderr)` — **this is the result**     | Must be clean JSON array only    |
| file     | Input written to `/tmp/xxx.json`, passed as arg   | Outer snippet reads via `items`  |

---

## The Contamination Chain

### Original broken flow (`n8n_PythonExtension.py` before fix)

```
naskio TS
  └─ spawn: python3 /tmp/snippet.py --json_path /tmp/input.json
      └─ snippet_runner(items)
          └─ process_with_minimal_memory()
              └─ subprocess.Popen(['python3', './scripts/03_initial_placer.py'], ...)
                  stdin  ← json.dumps(payload)
                  stdout → read by n8n_PythonExtension.py
                  stderr → print(stderr, file=sys.stderr)   ← WRITES TO OUTER STDERR ⚠️

              json.loads(stdout) → response
              return [response]

      sys.stderr.write(json.dumps(new_items))   ← appended AFTER the noise

naskio TS: JSON.parse("Traceback (most recent call last):\n[{...}]")
           → SyntaxError: Unexpected token r in JSON at position 1
              (T=0, r=1 → "Traceback")
```

---

## All Possible Root Causes of "Unexpected token r at position 1"

Position 0 = `T`, position 1 = `r` → the outer stderr starts with `"Traceback..."`.

| # | Cause | How `"Traceback..."` reaches outer stderr |
|---|-------|------------------------------------------|
| 1 | Inner script crashes (any exception) | `stderr='Traceback...'` forwarded by `print(stderr, file=sys.stderr)` in `n8n_PythonExtension.py` |
| 2 | `json.loads(stdout)` fails (empty stdout) | Inner crash → stdout empty → JSONDecodeError in snippet → Python prints traceback directly |
| 3 | Script path not found | `python3: can't open './scripts/...'` → stdout empty → JSONDecodeError traceback |
| 4 | Missing import in inner script | `ModuleNotFoundError` in inner → Traceback forwarded OR causes outer exception |
| 5 | Inner script warns + returns | `print(..., file=sys.stderr)` in `03_initial_placer_gif.py` (video path, feasibility warnings) forwarded → prefix to JSON |
| 6 | ffmpeg/imageio stderr | `imageio.mimwrite(codec="libx264")` spawns ffmpeg; ffmpeg writes progress to fd 2 of inner subprocess → forwarded |
| 7 | Python deprecation warnings | `warnings` module output on inner stderr → forwarded → prefix |

**Note:** Causes 2–4 exit with code 1 → naskio takes the `else` branch → `NodeOperationError`, not
`SyntaxError`. Causes 1, 5, 6, 7 (inner succeeds + has noise) produce the `SyntaxError`.

---

## The Fix Applied

**`n8n/workflows/n8n_PythonExtension.py`** now uses `run_n8n_script()` from this library.
`run_n8n_script()` captures inner stderr but **does not forward it**, keeping the outer stderr
channel clean for naskio's JSON.parse.

```python
# Before (broken)
if stderr:
    print(stderr, file=sys.stderr)   # ← contaminates naskio's JSON channel

# After (fixed) — inner stderr silently captured as _stderr, never forwarded
stdout, _stderr = proc.communicate(json_data)
```

See `run_n8n_script()` in [n8n_json_handler.py](n8n_json_handler.py).

---

## Quick Reference: Fixed Data Flow

```
naskio TS
  └─ spawn: python3 /tmp/snippet.py --json_path /tmp/input.json --env_vars {}
      │  (stdin never used by naskio)
      └─ snippet_runner(items, {})
          └─ run_n8n_script('./scripts/03_initial_placer.py', items)
              └─ Popen(['python3', script], stdin=PIPE, stdout=PIPE, stderr=PIPE)
                  stdin  ← json.dumps(payload)
                  stdout → json.loads(stdout) → response
                  stderr → _stderr  (captured, silenced)

          return [response]

      sys.stderr.write(json.dumps([response]))   ← outer stderr: clean JSON only

naskio TS: JSON.parse("[{...}]")  ✓
```
