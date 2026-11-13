# DWD presentation blocks

`format.js` is the presentation utility for the current warning's captured
source fields. `build.py` embeds it and the formatter/field block definitions
in the canonical `lhlab_alarm_library.yml`, without rebuilding other blocks.

```bash
python3 tools/dwd-messages/build.py
./tests/linter-check.sh
```

`verify.js` defines `verifyDwd(time, sources)` for an isolated check in the
installed JavaScript runtime. Supply openHAB's real `time` API and these source
strings, resolving the library utility name/dependency placeholders first:

| Source key | Function |
| --- | --- |
| `format` | `lhlab_dwd_text` |
| `process` | `lhlab_alarm_process` |
| `monitor` | `lhlab_dwd_monitor` |
| `rule` (optional) | Generated Blockly rule script |

The checks use synthetic Items and captured timers, memory and actions.
Supplying `rule` also verifies push/Alexa wiring with delivery intercepted.
No real warning Items, notification actions or announcement rules are invoked.
Coverage includes component selection, legacy memory upgrades, slot moves,
updates, clearance after reload, midnight, year boundaries, UTC input and both
daylight-saving transitions. A successful run returns an assertion count and
fixed frost-warning previews.

After deployment, open the rule in MainUI's Blockly editor, regenerate and save
with the installed generator, then rerun the isolated checks against that saved
script. Keep deployment snapshots and private connection details outside the
published tooling.
