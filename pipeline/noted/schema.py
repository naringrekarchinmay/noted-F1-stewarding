"""The fixed vocabularies every ruling is mapped onto.

Precedent search compares rulings by these labels, so they are deliberately
few and concrete. Each description is what the model sees in its prompt.
"""

from __future__ import annotations

INCIDENT_TYPES: dict[str, str] = {
    "collision": "causing a collision or contact between cars",
    "forcing_off": "forcing another driver off the track or not leaving racing room",
    "leaving_track_advantage": "leaving the track and gaining a lasting advantage (usually while overtaking or defending)",
    "track_limits": "exceeding track limits repeatedly, counted per infringement",
    "unsafe_rejoin": "rejoining the track unsafely after leaving it",
    "impeding": "impeding another car, usually in qualifying or practice",
    "erratic_driving": "erratic, unnecessarily slow or potentially dangerous driving, more than one change of direction, too slow between the safety car lines (SC1-SC2) in qualifying",
    "unsafe_release": "a car released unsafely from its pit stop",
    "pit_lane_speeding": "exceeding the pit lane speed limit",
    "pit_lane_procedure": "other pit lane rules: reversing, pit entry or exit lines, serving a penalty correctly",
    "flags": "ignoring yellow, blue or red flags",
    "safety_car": "safety car or virtual safety car rules: overtaking, gaps, restarts, the safety car's own procedure",
    "start_procedure": "the race start or formation lap: false start, grid position",
    "race_director_instruction": "not following the race director's event notes or instructions",
    "unsafe_car": "driving a car in an unsafe condition or throwing objects from it",
    "power_unit": "using more power unit elements than allowed",
    "gearbox": "using more gearbox or drivetrain parts than allowed",
    "parc_ferme": "working on the car under parc ferme conditions",
    "technical": "the car not complying with the technical regulations: scrutineering, weighing, deflection tests, DRS",
    "conduct": "conduct and procedures of a driver or team: language, unsportsmanlike behaviour, tyre returns, setup sheets, curfew, anthem, officials' instructions",
    "administrative": "requests and permissions: withdrawals, permission to race outside 107%, changes of driver",
    "other": "none of the above",
}

FACTORS: dict[str, str] = {
    "first_lap": "the incident happened on the first lap",
    "right_to_corner": "two cars fighting for a corner: which one had the right to it or to racing room under the Driving Standards Guidelines",
    "lasting_advantage": "the driver gained a lasting advantage",
    "no_advantage": "the driver gained no advantage",
    "position_given_back": "the position was given back",
    "sporting_consequence": "the other car lost time, a position, a lap or was damaged",
    "minimal_impact": "the effect on the other car was small or did not amount to an offence",
    "evasive_action": "another driver had to brake, swerve or take evasive action",
    "dangerous": "the stewards called the situation dangerous or a safety risk",
    "team_responsibility": "the team's error or lack of warning to the driver was a factor",
    "mitigation": "the stewards reduced the penalty because of mitigating circumstances",
    "conditions": "weather, visibility or track conditions were a factor",
    "benefit_of_doubt": "the evidence was inconclusive and the driver or team got the benefit of the doubt",
    "no_one_to_blame": "the stewards found that no driver was wholly or predominantly to blame",
    "guideline_penalty": "the penalty is fixed by the regulations or the penalty guidelines",
    "precedent": "the stewards referred to earlier cases or to the usual penalty for this offence",
    "regulation_interpretation": "the decision turns on how a regulation should be read",
}

OUTCOMES: dict[str, str] = {
    "penalty": "a penalty or warning was imposed",
    "no_further_action": "no further action, no penalty",
    "upheld": "a protest or request for review was upheld",
    "dismissed": "a protest or request for review was dismissed, rejected or inadmissible",
    "approved": "a request (withdrawal, re-scrutineering, change) was approved",
}

PENALTY_KINDS: dict[str, str] = {
    "time": "time penalty in seconds",
    "drive_through": "drive-through penalty",
    "stop_go": "stop and go penalty in seconds",
    "grid_drop": "drop of grid places",
    "pit_lane_start": "required to start from the pit lane",
    "back_of_grid": "start from the back of the grid",
    "reprimand": "reprimand",
    "warning": "formal warning",
    "fine": "fine in euros",
    "disqualification": "disqualification",
    "lap_time_deleted": "lap time deleted",
    "penalty_points": "penalty points on the driver's licence",
}
