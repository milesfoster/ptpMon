# Create parameters for polling here

# Device: Scorpion-X18


active_ptp = {
    "id": "875.0@i",
    "type": "integer",
    "name": "active_ptp",
}
ptp_status = {
    "id": "852.0@i",
    "type": "integer",
    "name": "ptp_status",
}
master_identity = {
    "id": "828.0@s",
    "type": "string",
    "name": "s_master_identity",
}
grandmaster_identity = {
    "id": "827.0@s",
    "type": "string",
    "name": "s_grandmaster_identity",
}
active_ptp_lookup = {
    0: "Main",
    1: "Backup",
}
ptp_status_lookup = {
    0: "Absent",
    1: "Un-Converged",
    2: "Converged",
}

# Insert params into the params list for import into main module

params = [
    active_ptp,
    ptp_status,
    master_identity,
    grandmaster_identity,

]

lookups = [
    active_ptp_lookup,
    ptp_status_lookup
]
