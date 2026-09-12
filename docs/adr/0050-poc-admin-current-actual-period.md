# POC administration is one interactive CLI; App Settings owns Current Actual Period

The POC needs one operator entry point without introducing an authenticated admin UI. `python -m backend.scripts.admin` provides four operations: set the global, Month-only Current Actual Period; import Budget; import Actual; and show status. Current Actual Period is independent of frontend Period selection: it is the latest historical Actual Month and the boundary after which Simulation starts from Budget. It is stored in the singleton `app_settings` row because Actual Import, Simulation, UI, and future application computations may share it; it is not Simulation-owned configuration. Budget Import filters friendly `year`/`period` CSV rows to a selected calendar year and replaces that Fiscal Year's Budget facts; Actual Import filters the same CSV shape to a selected Company plus Current Actual Period, reports skipped rows, and replaces only that Company's Actual facts for that Month.

## Status

accepted
