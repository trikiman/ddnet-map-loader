# Interrupt & Resume report

- blob_count: 20
- blob_size: 262144 bytes
- upstream: local synthetic HTTP server on port 61488
- types_root: C:\Users\rust-\AppData\Local\Temp\tmpzb8h9mvd\types

## Post-kill state (process hard-terminated by orchestrator)

- .map files present: 5
- partial (.ddnetcontrol-download-*) temp files: 1
  (expected to be >= 0 after hard kill — temp files are NOT visible as .map
   and the next run sweeps them; see post-resume state below.)
- zero-byte .map files: 0  (MUST be 0)

## Post-resume state

- .map files present: 20
- partial (.ddnetcontrol-download-*) temp files: 0
- all expected sizes: True
- files: ['synthetic/blob_00.map', 'synthetic/blob_01.map', 'synthetic/blob_02.map', 'synthetic/blob_03.map', 'synthetic/blob_04.map'] ... ['synthetic/blob_18.map', 'synthetic/blob_19.map']

## Assertions

- PASS: no zero-byte .map files visible after kill
- PASS: next-run sweep cleared all download orphans
- PASS: all 20 .map files present after resume
- PASS: all .map files have correct size after resume
