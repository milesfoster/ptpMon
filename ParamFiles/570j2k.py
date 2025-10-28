# Create parameters for polling here

# Device: 570J2K

active_ptp = {
"id": "736@i",
"type": "integer",
"name": "active_ptp",
}
ptp_status = {
    "id": "821@i",
    "type": "integer",
    "name": "ptp_status",
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
    active_ptp,
    ptp_status,
]

lookups = [
    active_ptp_lookup,
    ptp_status_lookup
]