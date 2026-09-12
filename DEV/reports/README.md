# Tracked DEV Reports

This directory contains tracked engineering and task reports for the OTG Analytics repository.

Reports numbered 001 and above are authoritative GitHub-visible reports. Each task uses `NNN_TASK_NAME/REPORT.md`.

Each implementation task normally has one implementation commit followed by one report-only commit. REPORT.md records the implementation SHA, not its own report commit SHA; the report commit SHA is obtained from Git history because a commit cannot reliably contain its own final SHA. Report-only commits must contain no application, test, or runtime changes. A report describes its specific implementation commit and does not imply that implementation remains the current develop HEAD forever; later application commits may exist. When no real browser validation occurred, VISUAL_VALIDATION remains HUMAN_VALIDATION_REQUIRED.

Reports must never contain secrets. A report PASS does not imply production deployment.

Historical reports created before this system may remain in the external DEV archive and are not required to be migrated.
