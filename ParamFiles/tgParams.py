# Create parameters for polling here

# Device: 570TG-100G

master_identity = {
    "id": "64@s",
    "type": "string",
    "name": "s_master_identity",
}
grandmaster_identity = {
    "id": "61@s",
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
    master_identity,
    grandmaster_identity,

]

lookups = [
    active_ptp_lookup,
    ptp_status_lookup
]