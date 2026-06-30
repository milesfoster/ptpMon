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

grandmaster_identity = {
    "id": "829@s",
    "type": "string",
    "name": "s_grandmaster_identity",
}

active_ptp_lookup = {
    0: "Main",
    1: "Backup",
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
    grandmaster_identity
]

lookups = [
    active_ptp_lookup,
    ptp_status_lookup
]