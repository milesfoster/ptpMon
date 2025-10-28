# Create parameters for polling here

# Device: Scorpion6F

active_ptp = {
"id": "5103@i",
"type": "integer",
"name": "active_ptp",
}
ptp_status = {
    "id": "5101@i",
    "type": "integer",
    "name": "ptp_status",
}
master_identity = {
    "id": "5102@s",
    "type": "string",
    "name": "s_master_identity",
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
    active_ptp,
    ptp_status,
    master_identity,
]

lookups = [
    active_ptp_lookup,
    ptp_status_lookup
]