# Create parameters for polling here

# Device: MIO-PTP  (no active_ptp reported; index 0 lookup kept for alignment)

ptp_status = {
    "id": "500@i",
    "type": "integer",
    "name": "ptp_status",
}
master_identity = {
    "id": "512@s",
    "type": "string",
    "name": "s_master_identity",
}
grandmaster_identity = {
    "id": "507@s",
    "type": "string",
    "name": "s_grandmaster_identity",
}
active_ptp_lookup = {
    0: "N/A",
    1: "Trunk 1",
    2: "Trunk 2",
}
ptp_status_lookup = {
    0: "Absent",
    1: "Unlocked",
    2: "Locked",
}

# Insert params into the params list for import into main module

params = [
    ptp_status,
    master_identity,
    grandmaster_identity,
]

lookups = [
    active_ptp_lookup,
    ptp_status_lookup
]
