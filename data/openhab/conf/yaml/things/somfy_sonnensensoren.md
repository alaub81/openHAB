# Somfy sun sensors defined in YAML

The YAML templates describe the east, south, and west sun sensors. They were
prepared to reduce unnecessary writes to the openHAB server's SD card.

During the investigation on 2026-10-31, the Somfy binding was observed updating
brightness values as Thing properties (`core:LuminanceState`). For the south
sensor managed through the UI, one such change caused the entire Thing JSONDB
file, approximately 2.55 MB, and an equally large backup to be rewritten.

A file-based YAML Thing definition was therefore prepared as a workaround.
According to the source review at the time, property changes for file-managed
Things do not go through the managed JSONDB storage. The goal is to avoid these
repeated writes and keep the sensor configuration traceable in the repository.
The actual reduction had not yet been measured on the running system.

The files currently end in `.yml.example` and are **inactive templates**. Their
presence does not mean the sensors have already been migrated. A future migration
must preserve existing Thing UIDs, bridge assignments, and Item links. The same
Thing UID must not be defined through the UI and YAML simultaneously. After the
migration, configuration is maintained in the YAML file.

Evidence: local investigation reports in
`archive/somfy-storage-review-20261031/bericht.txt` and
`archive/sdcard-review-20261031-1100/bericht.txt`.
