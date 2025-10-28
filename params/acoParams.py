# Create parameters for polling here

# Device: 570IPG-X19-25G  (and 10G, but Clock identity is not reported)

active_ptp = {
"id": "875@i",
"type": "integer",
"name": "active_ptp",
}
ptp_status = {
    "id": "852@i",
    "type": "integer",
    "name": "ptp_status",
}
master_identity = {
    "id": "828@s",
    "type": "string",
    "name": "s_master_identity",
}
grandmaster_identity = {
    "id": "827@s",
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