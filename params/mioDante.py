# Create parameters for polling here

# Device: MIO-DANTE
# Reports two grandmasters (main + backup port); active_ptp selects which port
# PTP is locked to. See dual_gm below and parse_results in ptpMon.py.

ptp_status = {
    "id": "803@i",
    "type": "integer",
    "name": "ptp_status",
}
active_ptp = {
    "id": "805@i",
    "type": "integer",
    "name": "active_ptp",
}
grandmaster_main = {
    "id": "804.0@s",
    "type": "string",
    "name": "s_grandmaster_identity_main",
}
grandmaster_backup = {
    "id": "804.1@s",
    "type": "string",
    "name": "s_grandmaster_identity_backup",
}
active_ptp_lookup = {
    0: "N/A",
    1: "Main",
    2: "Backup",
}
ptp_status_lookup = {
    0: "Absent",
    1: "Unlocked",
    2: "Locked",
}

# Insert params into the params list for import into main module

params = [
    ptp_status,
    active_ptp,
    grandmaster_main,
    grandmaster_backup,
]

lookups = [
    active_ptp_lookup,
    ptp_status_lookup
]

# Dual-grandmaster selection. parse_results uses the raw active_ptp value to pick
# which port's GM becomes the canonical s_grandmaster_identity. ports keys are the
# raw active_ptp ints; raw 0 (or any unmapped value) falls through to "N/A".
dual_gm = {
    "active_name": "active_ptp",
    "ports": {1: "s_grandmaster_identity_main", 2: "s_grandmaster_identity_backup"},
    "canonical": "s_grandmaster_identity",
}
