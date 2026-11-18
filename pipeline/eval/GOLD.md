# Gold set for checking

Each ruling's own words, then the labels Claude gave it. If a label is wrong, change it in
`gold.json` (or tell Claude). Factor and type meanings are in `noted/schema.py`.

## 4: Doc 79 - Infringement - Car 16 - Causing a collision

**Fact.** Car 16 made contact with Car 30 in turn 12.

**Decision.** 5 second time penalty. (5 seconds added to elapsed Race time).

**Reason.** The Stewards heard from the driver of Car 16 (Charles Leclerc), the driver of Car 30 (Liam Lawson), team representatives and reviewed positioning/marshalling system data, video and in-car video evidence and determined that Car 16 made contact with Car 30 at turn 12. While the contact was minor and Car 30 was able to maintain the lead thereafter, the driver of Car 30 claimed that the contact damaged the rear left rim of his car and also enabled Car 16 to get closer to him on track and then eventually overtake him 5 corners later. Furthermore, under the Driving Standard Guidelines, Car 30 had the right to the corner and it was for Car 16 to take the necessary steps to avoid a collision. The driver of Car 16 claimed that it was a minor contact with no obvious sporting consequence. While we acknowledge that the contact was minor, having examined the fight on track between the two cars, we conclude that Car 16 was able to get closer to and thereafter overtake Car 30 because of the contact. The contact clearly disrupted Car 30 and allowed Car 16 to pull up alongside when it was further away before the contact. This was an obvious sporting consequence. In mitigation, the wet conditions coupled with the nature of the contact (ie minor) was taken into account in imposing a 5 second time penalty as opposed to a 10 second time penalty.

- Type: `collision`
- Outcome: `penalty`
- Penalties: time 5
- Factors: `right_to_corner`, `sporting_consequence`, `mitigation`, `conditions`
- Either way: `minimal_impact`, `precedent`

## 12: Doc 71 - Infringement - Car 27 - Leaving the track and gaining an advantage

**Fact.** Car 27 left the track and gained a lasting advantage.

**Decision.** 10 second time penalty.

**Reason.** The Stewards reviewed in-car video evidence and determined that Car 27 left the track while attempting to overtake Car 43 at Turn 1 on the outside. Car 27 then rejoined the track ahead of Car 43. Car 43 was ahead at the apex of Turn 1 and had the right to the corner per the Driving Standards Guidelines. Car 27 gained a lasting advantage by leaving the track. We imposed a 10 second time penalty on Car 27.

- Type: `leaving_track_advantage`
- Outcome: `penalty`
- Penalties: time 10
- Factors: `right_to_corner`, `lasting_advantage`

## 16: Doc 67 - Infringement - Car 23 - Rejoining the track unsafely

**Fact.** Car 23 rejoined the track in an unsafe manner.

**Decision.** 5 second time penalty. 2 penalty points (total of 3 for the 12 month period).

**Reason.** The Stewards reviewed positioning/marshalling system data, video and in-car video evidence and determined that Car 23 left the track at Turn 2 and rejoined at Turn 3 in front of Car 10, which was forced to brake. Cars on track should not be forced to slow down to accommodate a car rejoining the track. We accordingly imposed a 5 second time penalty per the applicable guidelines.

- Type: `unsafe_rejoin`
- Outcome: `penalty`
- Penalties: time 5, penalty_points 2
- Factors: `evasive_action`, `guideline_penalty`

## 17: Doc 66 - Decision - Car 11 - Alleged failure to slow under yellow flags

**Fact.** Car 11 alleged failure to slow for double yellow flags.

**Decision.** No further action.

**Reason.** The Stewards reviewed positioning/marshalling system data, video, timing, telemetry, and in-car video evidence. The double yellow flags were triggered following an incident involving Car 51 (CAM), who lost control at Turn 1 immediately ahead of Car 11 (PER). The Stewards noted that PER had very limited time to react, as he was already approaching Turn 1 and had commenced braking when the double yellow flags were activated. The telemetry showed that PER braked more than on comparable laps and carried a lower speed through Turns 2 and 3. Furthermore, the time taken to complete the marshalling sector in which the double yellow flags were displayed was discernibly longer than on comparable laps. Taking all these elements into account, the Stewards were satisfied that PER reacted appropriately to the double yellow flags and reduced his speed sufficiently in the circumstances. The Stewards therefore determined that no further action was necessary.

- Type: `flags`
- Outcome: `no_further_action`
- Penalties: none
- Factors: none
- Either way: `conditions`

## 18: Doc 65 - Decision - Car 44 - Alleged leaving the track and gaining an advantage

**Fact.** Car 44 allegedly left the track at turn 5 and gained a lasting advantage.

**Decision.** No further action.

**Reason.** The Stewards reviewed in-car video evidence and determined that Car 44 was attempting an overtake on Car 87 at Turn 5. In defending the position, Car 87 moved to the right and Car 44 was pushed off the track to avoid a collision. Car 44 clearly had the momentum for the overtake and gained no advantage by going off the track. We also noted that the position was subsequently given back by Car 44. We therefore took no further action.

- Type: `leaving_track_advantage`
- Outcome: `no_further_action`
- Penalties: none
- Factors: `no_advantage`, `position_given_back`
- Either way: `evasive_action`, `right_to_corner`

## 58: Doc 25 - Infringement - Car 51 - Unnecessarily impeding of Car 16

**Fact.** Car 51 unnecessarily impeded Car 16 in turn 15.

**Decision.** Driver: Reprimand (Driving). This is the driver’s 1st reprimand of the season.

**Reason.** The Stewards heard from the driver of Car 51 (Rafael Camara), team representatives and reviewed video, team radio and in-car video evidence and determined that Car 51 was warned multiple times that Car 16 (LEC) was arriving on a fast lap. Yet, Car 51 was weaving and moving well into the racing line. Car 16 had to take evasive action to avoid a collision by moving to the right, with a significant amount of the car off the track. The situation that was created was clearly dangerous and Car 51 should have taken more care to avoid impeding Car 16. While the typical penalty for impeding in a Free Practice session is a warning, in this instance, we are of the view that a reprimand is warranted.

- Type: `impeding`
- Outcome: `penalty`
- Penalties: reprimand
- Factors: `dangerous`, `evasive_action`, `precedent`

## 42: Doc 41 - Infringement - Car 87 - Reversing in the Pit Lane

**Fact.** Car 87 reversed in the Pit Lane.

**Decision.** Driver: Reprimand (Driving). This is the driver’s 2nd reprimand of the season.

**Reason.** The Stewards reviewed in-car video evidence and determined that Car 87 reversed in the pit lane under its own power. This is expressly prohibited under Article B1.6.3b of the FIA F1 Regulations. We therefore imposed a driving reprimand on the driver of Car 87 (BEA).

- Type: `pit_lane_procedure`
- Outcome: `penalty`
- Penalties: reprimand
- Factors: none

## 93: Infringement - Car 21 - Forcing another driver off the track

**Fact.** Car 21 forced Car 20 off the track at turn 6.

**Decision.** 5 second time penalty. 2 penalty points (total of 2 for the 12 month period)

**Reason.** The Stewards reviewed video, and in-car video evidence. At and from the apex of Turn 6, Car 20 was on the outside and was clearly level and then in front of Car 21.  In accordance with the Driving Standards Guidelines, Car 20 should have been given racing room.

- Type: `forcing_off`
- Outcome: `penalty`
- Penalties: time 5, penalty_points 2
- Factors: `right_to_corner`

## 92: Decision - Car 22 - Alleged unsafe release

**Fact.** Alleged failure to serve a penalty during a pit stop.

**Decision.** No further action.

**Reason.** Video evidence from the FIA pit box overhead camera shows the jack moving towards the front of the car as the car stops.  It appears very close but after the expiration of the 5 second time penalty, there appears to be a small further forward movement leading us to have doubt as to whether the jack was touching the car during the penalty period.  In this case the competitor is given the benefit of the doubt.

- Type: `pit_lane_procedure`
- Outcome: `no_further_action`
- Penalties: none
- Factors: `benefit_of_doubt`
- Note: The title says unsafe release, but the matter is whether a penalty was served correctly.

## 95: Infringement - Car 31 - Unsafe release

**Fact.** Unsafe release of car 31

**Decision.** 5 second time penalty

**Reason.** The Stewards reviewed video and in-car video evidence. Car 2 was seen to have to significantly slow to avoid Car 31 which was exiting the pit whilst Car 2 was attempting to enter the pit box.  Video also showed that Car 31 was released after Car 2 had passed the relevant pit lane marker.

- Type: `unsafe_release`
- Outcome: `penalty`
- Penalties: time 5
- Factors: `evasive_action`

## 119: Infringement - Car 16 - Impeding Car 81

**Fact.** Car 16 unnecessarily impeded Car 81 in turn 9 at 12:09.

**Decision.** Drop of 3 grid positions for the next race in which the driver participates.

**Reason.** The Stewards heard from the driver of Car ​16 (Charles Leclerc), the driver of Car 81 (Oscar Piastri), team representatives and reviewed positioning/marshalling system data, video, timing, telemetry, team radio and in-car video evidence. The driver of Car 81 stated that as he approached Turn 9 he saw that Car 16 was travelling slowly and had to brake, reducing his speed by approximately 45 km/h over the previous push lap.  This was verified by the Stewards referencing the telemetry of Car 81.  It was confirmed Car 81 lost approximately 0.5 of a second in that mini- sector (5.3s v 4.8s). The driver of Car 16 stated that the last call he had from his team was when he was approaching Turn 4 (“Piastri 6 seconds”) and that he saw Car 81 in his mirrors as he was in Turn 8 and Car 81 was in Turn 7. The Team Representative of Car 16 stated that the team “could have done better” in communicating the rapid approach of Car 81 and its drivers stated that “If I had been warned I could have done something earlier”. Accordingly we determine that although this was not entirely the fault of the driver, and that the team’s lack of communication was the major contributing factor, a grid position penalty must be imposed as Car 81 was “unnecessarily impeded”, because there is no doubt that the situation could have been avoided. It should also be noted that this penalty is to apply ONLY to the Sprint and should the driver be unable to contest the Sprint at this event, the penalty shall carry over to the next Sprint (and not the Grand Prix).

- Type: `impeding`
- Outcome: `penalty`
- Penalties: grid_drop 3
- Factors: `sporting_consequence`, `team_responsibility`
- Either way: `evasive_action`

## 131: Decision - Alleged impeding of Car 20

**Fact.** Car 1 allegedly unnecessarily impeded Car 20 in turn 1.

**Decision.** No further action.

**Reason.** The Stewards heard from the driver of Car ​1 (Max Verstappen), the driver of Car ​20 (Kevin Magnussen), team representatives and reviewed positioning/marshalling system data, video, timing, telemetry, team radio and in-car video evidence. The driver of Car 1 stated that he saw a car approaching after he crossed the line at the end of his push lap and moved to the left of the track after the exit of Turn 1. The driver of Car 20 stated that he had to move to the right to avoid Car 1 and hence lost time on his fast lap. The Stewards determined from the video (and audio) evidence that Car 20 had clipped the kerb in Turn 1 and that this subsequently caused a slight change in acceleration which in turn resulted in a slightly slower time on the next mini sectors. The Stewards further determined that Car 20 did not have to take significant evasive action. We further note that the fact that the lap time of Car 20 was subsequently deleted (due to exceeding track limits at Turn 10) was irrelevant to this decision. Any incident is always investigated independently of other incidents or penalties.

- Type: `impeding`
- Outcome: `no_further_action`
- Penalties: none
- Factors: `minimal_impact`

## 84: Infringements - Leaving the track multiple times

**Fact.** Leaving the track without a justifiable reason multiple times.

**Decision.** Penalties below imposed after the race, added to elapsed race time. No No / Driver Competitor Penalty 1 55 – Carlos Sainz Scuderia Ferrari 10 second time penalty 2 44 – Lewis Hamilton Mercedes AMG-Petronas F1 Team 10 second time penalty 3 10 – Pierre Gasly BWT Alpine F1 Team 10 second time penalty 4 23 – Alexander Albon Williams Racing 10 second time penalty 5 31 – Esteban Ocon BWT Alpine F1 Team 5 second time penalty 6 31 – Esteban Ocon BWT Alpine F1 Team 10 second time penalty 7 31 – Esteban Ocon BWT Alpine F1 Team 5 second time penalty 8 31 – Esteban Ocon BWT Alpine F1 Team 10 second time penalty 9 2 – Logan Sargeant Williams Racing 10 second time penalty 10 21 – Nyck de Vries Scuderia AlphaTauri 10 second time penalty 11 21 – Nyck de Vries Scuderia AlphaTauri 5 second time penalty 12 22 – Yuki Tsunoda Scuderia AlphaTauri 5 second time penalty

**Reason.** Penalties have been applied as follows: For four infringements, a 5 second time penalty; for five infringements, a 10 second time penalty. Then a “reset” has been allowed due to the excessive number of infringements. The counting of infringements restarts. After another four infringements, a 5 second time penalty will apply; after five, a 10 second time penalty. The Stewards very strongly recommend that a solution be found to the track limits situation at this circuit.

- Type: `track_limits`
- Outcome: `penalty`
- Penalties: time 10 55, time 10 44, time 10 10, time 10 23, time 5 31, time 10 31, time 5 31, time 10 31, time 10 2, time 10 21, time 5 21, time 5 22
- Factors: `guideline_penalty`

## 181: Offence - Car 31 - Impeding Car 5 in turn 16

**Fact.** Impeding of Car 5 by Car 31 in Turn 16.

**Decision.** Reprimand for the driver (This is the driver’s 2nd Reprimand of the Season, 1st Driving Reprimand) A fine of €10,000 is imposed on the Competitor (Alpine F1 Team)

**Reason.** The Stewards heard from the driver of Car 31 (Esteban Ocon), the driver of Car 5 (Sebastian Vettel) and team representatives, and examined video, team radio and telemetry evidence. In evidence, the driver of Car 31 stated that he was given a warning that Car 5 was 2.5 seconds behind between Turns 15 and 16.  However, due to the track layout he had no visibility of Car 5 until Turn 16 and hence had no time to react. This incident shared many common elements with the other incidents of alleged impeding from Qualification.  Most cars did very slow warm up laps resulting in significantly large differences in speed to cars on fast laps.  This combined with the desire of all drivers to establish a gap to the car in front when starting a fast lap, results in situations where a car may have an “impact” on another car doing a fast lap.  However, the Stewards consider this is different to “impeding” and in particular, “unnecessarily impeding”. It is the Stewards’ determination that the driver of Car 31 could have done little if anything to avoid impacting Car 5’s lap, but note that the Team could have done more to have given him earlier warning of Car 5’s approach. Although normally the lack of radio communication does not absolve a driver from the responsibility to avoid unnecessarily impeding, in this case we consider this a justification for mitigation. Therefore, no grid penalty is imposed.

- Type: `impeding`
- Outcome: `penalty`
- Penalties: reprimand, fine 10000 competitor
- Factors: `team_responsibility`, `mitigation`
- Either way: `minimal_impact`

## 177: Decision - Car 5 - Alleged impeding of car 10 in turn 1

**Fact.** Alleged Impeding of Car 10 by Car 5 in Turn 1.

**Decision.** No further action.

**Reason.** The Stewards heard from the driver of Car 5 (Sebastian Vettel), the driver of Car 10 (Pierre Gasly) and team representatives, and examined video, team radio and telemetry evidence. The Stewards note that almost certainly there was “dirty air” created by Car 5 which did have an “impact” on Car 10 however the Stewards determine that this does not amount to “unnecessarily impeding”.

- Type: `impeding`
- Outcome: `no_further_action`
- Penalties: none
- Factors: none
- Either way: `minimal_impact`

## 221: Offence - Car 5 (re-joinged unsafely and forced car 44 of the track)

**Fact.** Car 5 left the track, re-joined unsafely and forced another car off track.

**Decision.** 5 second time penalty (2 point awarded, 7 points in total for the 12 month period)

**Reason.** The stewards reviewed video evidence and determined that Car 5,left the track at turn 3, rejoined the track at turn 4 in an unsafe manner and forced car 44 off track. Car 44 had to take evasive action to avoid a collision.

- Type: `unsafe_rejoin or forcing_off`
- Outcome: `penalty`
- Penalties: time 5, penalty_points 2
- Factors: `evasive_action`

## 235: Offence - Car 55 (Impeding car 23 in turn 2)

**Fact.** Car 55 unnecessarily impeded car 23 at turn 2.

**Decision.** A drop of 3 grid positions in accordance with Article 31.4 of the Formula One Sporting Regulations. (1 penalty point awarded, 4 points in total for the 12 month period).

**Reason.** The Stewards reviewed video evidence and heard from the driver of car 55 (Carlos Sainz) and the driver of car 23 (Alexander Albon) and the team representatives. ALB was on a fast lap when he closed the gap to SAI, who was driving slowly on the racing line at Turn 2. SAI was on the radio with the Team, talking about tyres. The Team’s warning about ALB approaching was given too late. Because of this, ALB had to abort his lap.

- Type: `impeding`
- Outcome: `penalty`
- Penalties: grid_drop 3, penalty_points 1
- Factors: `team_responsibility`, `sporting_consequence`

## 247: Decision - Car 8 (Incident with car 18 in Turn 13)

**Fact.** Collision between Cars 8 and 18 at Turn 13.

**Decision.** No Further Action.

**Reason.** The Stewards reviewed video evidence, heard from the driver of car 8 (Romain Grosjean), the driver of car 18 (Lance Stroll) and the team representatives. While it was clear that the left rear wheel of Car 18 touched the right front wheel of Car 8 under braking at the entrance to Turn 13, none of the Drivers were predominantly to blame. The Stewards therefore concluded to take no further action.

- Type: `collision`
- Outcome: `no_further_action`
- Penalties: none
- Factors: `no_one_to_blame`

## 86: Decision - Aston Martin Protest

**Text (first 1,200 characters).** 2023 AUSTRIAN GRAND PRIX 30 June - 02 July 2023 The Stewards having received a protest from Aston Martin Aramco Cognizant F1 Team, having summoned (Doc 70) and heard from the Team Representative (Andy Stevenson), Nikolas Tombazis representing the FIA and Diego Ioverno representing Scuderia Ferrari, have considered the following matter and determine the following: Time: 1655 hrs (Publication of Provisional Classification) Session: Race The protest was lodged against the accuracy of the Provisional Classification. The Stewards first considered if the protest was admissible. The Stewards determined that as it was lodged on time and complied with the requirements of Chapter 13 of the FIA International Sporting Code, it was an admissible protest. An examination of the list of deleted lap times provided to the Stewards by Race Control, revealed that a number of track limit infringements had not previously been referred to the Stewards for potential penalty. It was determined that some of these infringements warranted a penalty that was not previously applied when the Provisional Classification was published. These penalties will be reflected in the Final Classification. Accordingly, the …

- Type: `track_limits`
- Outcome: `upheld`
- Penalties: none
- Factors: none
- Note: Protest against the provisional classification over unpenalised track limits; the penalties themselves are in another document.

## 101: Decision - McLaren - Right of Review

**Text (first 1,200 characters).** 2023 AUSTRIAN GRAND PRIX 30 June - 02 July 2023 The Stewards From The Stewards To The Team Manager, McLaren F1 Team Document 57 Date 02 July 2023 Time 13:35 Title Decision - McLaren Right of Review Description Decision - McLaren Right of Review Enclosed AUT DOC 57 - McLaren Right of Review (Canada).pdf Garry Connelly Mathieu Remmerie Enrique Bernoldi Walter Jobst 1 2023 AUSTRIAN GRAND PRIX 30 June – 02 July 2023 From The Stewards Document 57 To The Team Manager, Date 02 July 2023 McLaren F1 Team Time 13:35 1. On June 30, 2023 the Stewards received a petition from McLaren F1 Team requesting a Right of Review in accordance with Article 14 of the FIA International Sporting Code. 2. The request related to the Decision of the Stewards contained in document number 58 from the 2023 Canadian Grand Prix which imposed a 5 second time penalty on Car 4, for a breach of Article 12.2.1.l of the FIA International Sporting Code. 3. A hearing was convened at 0930 hrs Sunday July 2, 2023 and concerned parties were summoned (document numbers 31 and 32). 4. The FIA Stewards of the Canadian Grand Prix conducted the hearing. The FIA exercising its authority under Article 14.1.1, appointed Mr Walter Jobs…

- Type: `safety_car or conduct`
- Outcome: `dismissed`
- Penalties: none
- Factors: `precedent`, `regulation_interpretation`
- Note: Review of a 5 second penalty for Car 4 creating a gap behind the safety car (Canada 2023). That penalty is not imposed by this document.

## 160: Decision - Mercedes Protest Art. 48.12

**Text (first 1,200 characters).** From The Stewards To All Teams, All Officials Document 58 Date 12 December 2021 Time 23:03 2021 ABU DHABI GRAND PRIX 9 - 12 December 2021 The Stewards Title Decision - Mercedes Protest Art. 48.12 Description Decision - Mercedes Protest Art. 48.12 Enclosed UAE DOC 58 - Mercedes Protest Art 48.12.pdf Garry Connelly Felix Holter Derek Warwick Mohamed Al Hashmi 2021 ABU DHABI GRAND PRIX 9 – 12 December 2021 From The Stewards Document 58 To All Teams Date 12 December 2021 Time 23:03 Protest filed by Mercedes-AMG Petronas F1 Team against the Classification established at the end of the Competition Stewards Decision: The Protest is dismissed. Procedure: 1. On December 12 the parties were summoned at 2015 hrs (Documents 54 and 55) and heard. The following persons were present during the hearing: On behalf of Mercedes: ‐ Ron Meadows ‐ Andrew Shovlin ‐ Paul Harris (Team Legal Counsel) On behalf of Red Bull: ‐ Jonathan Wheatley ‐ Christian Horner ‐ Adrian Newey ‐ Red Bull, as an “interested party” was permitted to attend. The hearing adjourned at 2050 to allow Red Bull to consider its response in further detail and reconvened at 2130hrs. The Race Director was present for the reconvened hearin…

- Type: `safety_car`
- Outcome: `dismissed`
- Penalties: none
- Factors: `regulation_interpretation`

## 161: Decision - Mercedes Protest Art. 48.8

**Text (first 1,200 characters).** From The Stewards To All Teams, All Officials Document 57 Date 12 December 2021 Time 22:15 2021 ABU DHABI GRAND PRIX 9 - 12 December 2021 The Stewards Title Decision - Mercedes Protest Art. 48.8 Description Decision - Mercedes Protest Art. 48.8 Enclosed UAE DOC 57 - Mercedes Protest Art 48.8.pdf Garry Connelly Felix Holter Derek Warwick Mohamed Al Hashmi 2021 ABU DHABI GRAND PRIX 9 – 12 December 2021 From The Stewards Document 57 To All Teams Date 12 December 2021 Time 22:14 Protest filed by Mercedes-AMG Petronas F1 Team against Car number 33, driven by Max Verstappen (Red Bull Racing Honda) Stewards Decision: The Protest is dismissed. Procedure: 1. On December 12 the parties were summoned at 1945 hrs (Documents 52 and 53) and heard. The following persons were present during the hearing. On behalf of Mercedes: ‐ Ron Meadows ‐ Andrew Shovlin ‐ Paul Harris (Team Legal Counsel) On behalf of Red Bull: ‐ Jonathan Wheatley 2. At the hearing there were no objections against the composition of the Stewards panel. The parties set out oral arguments and addressed the questions asked by the Stewards. 3. At the hearing the parties referred to the documents submitted. None of the parties submit…

- Type: `safety_car`
- Outcome: `dismissed`
- Penalties: none
- Factors: none
- Either way: `minimal_impact`, `regulation_interpretation`

## 175: Decision - Car 9 - withdrawal from the event

**Text (first 1,200 characters).** From The Stewards To All Teams, All Officials Document 43 Date 12 December 2021 Time 12:42 2021 ABU DHABI GRAND PRIX 9 - 12 December 2021 The Stewards have received a request from the Haas F1 Team, to withdraw Car 9 from the Competition on the grounds of force majeure. This request is approved. The Stewards Garry Connelly Felix Holter Derek Warwick Mohamed Al Hashmi…

- Type: `administrative`
- Outcome: `approved`
- Penalties: none
- Factors: none

## 232: Decision - Car 20 (re-scrutineering request)

**Text (first 1,200 characters).** From The Stewards To The Team Manager, Rich Energy Haas F1 Team Document 32 Date 08 June 2019 Time 18:13 2019 CANADIAN GRAND PRIX 6 - 9 June 2019 The Stewards have received a request from Rich Energy Haas F1 Team to re-scrutineer car 20 which has had a change of the survival cell. In accordance with Article 25.2 and Article 25.4 of the FIA Formula One Sporting Regulations, the Stewards agreed that this can take place on June 9th before 12:00hrs Local Time. In accordance with Art 23.2 the car will be required to start the race from the pit lane. The Stewards Gerd Ennser Mathieu Remmerie Emanuele Pirro Mike Kaerne…

- Type: `administrative or technical`
- Outcome: `approved`
- Penalties: pit_lane_start
- Factors: none
- Either way: `guideline_penalty`

## 43: Doc 40 - Infringement - Car 11 - Driving in an unsafe condition

**Fact.** Car 11 drove in an unsafe condition.

**Decision.** Competitor: Formal warning.

**Reason.** The Stewards heard from the team representative and reviewed in-car video evidence and determined that the driver of Car 11 threw a small plastic piece out of the car. The plastic piece was a cable organiser that typically attaches to the seat belt. It dislodged during the session and the driver threw it out as he was concerned that it would lodge itself somewhere else in the car and create a safety issue. While we appreciated the fact that it was a small, light piece of plastic that was unlikely to cause any damage to another car or injure another driver, throwing materials onto the track during a live session is not appropriate for obvious reasons. We therefore issue a formal warning to the competitor to avoid similar situations from arising in the future.

- Type: `unsafe_car`
- Outcome: `penalty`
- Penalties: warning competitor
- Factors: none
- Either way: `minimal_impact`, `dangerous`

## 67: Doc 16 - Infringement - Car 43 - Pit Lane Speeding

**Fact.** Pit lane speeding – 80.6 km/h

**Decision.** The competitor (BWT Alpine F1 Team) is fined €100.

**Reason.** Car 43 exceeded the pit lane speed limit which is set at 80 km/h for this event by 0.6 km/h.

- Type: `pit_lane_speeding`
- Outcome: `penalty`
- Penalties: fine 100 competitor
- Factors: none

## 40: Doc 43 - Infringement - Car 44 - Additional changes to PU elements

**Fact.** The following Power Unit elements have been used: 6th Engine (ICE) 5th Turbocharger (TC) 5th Exhaust Set (EXH) 4th Energy Store (ES) 4th Control Electronics Unit (PU-CE) 4th MGU-K 7th Power Unit Ancillary Component (PU-ANC)

**Decision.** Drop of 65 grid positions for the next Race in which the driver participates.

**Reason.** The penalty is imposed in accordance with Article B8.2.8 of the FIA F1 Regulations. In this case, the use of the ICE additional element carries a 5 grid place penalty by virtue of Article B8.2.8b of the FIA F1 Regulations and the use of the TC, EXH, ES, PU-CE, MGU-K and PU-ANC additional elements carries a 10 grid place penalty by virtue of Article B8.2.8a of the FIA F1 Regulations. Therefore there is an accumulation of 65 places in addition to the 10 grid places (Document 37). Subject to Car 44 being classified in the results of Qualifying, Car 44 will be allocated a grid position in the Race in accordance with Article B2.5.4b.iv of the FIA F1 Regulations.

- Type: `power_unit`
- Outcome: `penalty`
- Penalties: grid_drop 65
- Factors: `guideline_penalty`

## 23: Doc 60 - Infringement - Car 27 - Failure to follow Race Directors Instruction - Practice Start

**Fact.** Car 27 did not cross the pit exit white line at the earliest opportunity.

**Decision.** Driver: Reprimand (Driving). This is the driver’s 3rd reprimand of the season.

**Reason.** The Stewards reviewed video evidence and determined that Car 27 which did not perform a practice start did not cross the white line separating the Pit Exit Road from the track at the earliest opportunity and join the “normal” racing line as required. This is a breach of the Race Director’s Competition Note.

- Type: `race_director_instruction or pit_lane_procedure`
- Outcome: `penalty`
- Penalties: reprimand
- Factors: none

## 102: Infringement - Car 21 - Changes made during Parc Ferme

**Fact.** The following Power Unit elements have been used: 3rd Energy Store (ES) 3rd Control Electronics (CE) All Power Unit elements were replaced without the approval of the FIA Technical Delegate during Parc Ferme. The suspension setup has been changed while under Parc Fermé. The rear wing and beam wing have been changed to a different specification than that which was used during qualifying

**Decision.** Required to start the Race from the pit lane.

**Reason.** The Power Unit elements have been changed. The setup was modified whilst the car was in parc fermé without the approval of the Technical Delegate. The wing setup has been changed from that previously used in Qualifying. The competitor is therefore required to start the race from the pit lane per article 40.9 of the FIA Formula One Sporting Regulations.

- Type: `parc_ferme`
- Outcome: `penalty`
- Penalties: pit_lane_start
- Factors: `guideline_penalty`

## 225: Offence - Car 20 (PU Element - CE)

**Fact.** A 3rd Control Electronics (CE) has been used.

**Decision.** Drop of 10 grid positions.

**Reason.** The penalty is imposed in accordance to with Article 23.3 b) of the FIA Formula One Sporting Regulations. This penalty does not change the fact that the competitor is required to start from the Pit Lane for a prior infringement (document 32).

- Type: `power_unit`
- Outcome: `penalty`
- Penalties: grid_drop 10
- Factors: `guideline_penalty`
