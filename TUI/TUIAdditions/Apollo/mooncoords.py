class Retros:

  def __init__(self):
    self.target = 'A11'		# which retro? dictionary pts to coords

#    self.selenolong={'A11':23.4711, 'Luna17':-35.2177, 'A14':-17.477,
#                     'A15':3.6196, 'Luna21':30.6}
#    self.selenolat={'A11':0.6729, 'Luna17':38.3050, 'A14':-3.6457,
#                    'A15' :26.1291, 'Luna21':26.5}

    self.names = ["Apollo 11", "Luna 17", "Apollo 14", "Apollo 15", "Luna 21"]
    self.lookup = {"Apollo 11":"A11", "Luna 17":"LUNA17","Apollo 14":"A14",
                   "Apollo 15":"A15", "Luna 21":"LUNA21"}

# these coordinates do not effect tracking: only for plotting on pointer!
# pointing is handled by entries in features.dat; part of ephem/moon_pos.py
    self.long = {"Apollo 11":23.45864,
                "Luna 17":-35.0338,
                "Apollo 14":-17.49269,
                "Apollo 15":3.61476,
                "Luna 21":30.91310}

    self.lat = {"Apollo 11":0.69347,
                "Luna 17":38.3430,
                "Apollo 14":-3.62328,
                "Apollo 15":26.15515,
                "Luna 21":25.85094}

    self.codes = {"Apollo 11": 0,
                  "Luna 17": 1,
                  "Apollo 14": 2,
                  "Apollo 15": 3,
                  "Luna 21": 4}

class Finders:

  def __init__(self):
    self.names = ["Moltke", "Torricelli C", "Blagg", "Messier", "Messier B",
                  "Turner F", "Fra Mauro B",
                  "Nearby Knob", "Archimedes C", "Archimedes D",
                  "Brewster", "Le Monnier C", "Luther",
                  "Bruce", "Webb", "Peirce", "Lohrmann A", "Damoiseau E",
                  "Milichius", "Milichius A", "Mairan E", "Puiseux D",
                   "Nicolai A",
                  "North Limb", "South Limb", "East Limb", "West Limb"]

    self.lookup = {"Apollo 11":"A11", "Moltke":"MOLTKE",
                   "Torricelli C":"TORRICELLI_C",
                   "Blagg":"BLAGG", "Messier":"MESSIER","Messier B":"MESSIER_B",
                   "Apollo 14":"A14", "Turner F":"TURNER_F",
                   "Fra Mauro B":"FRA_MAURO_B",
                   "Apollo 15":"A15", "Nearby Knob":"UNK_KNOB",
                   "Archimedes C":"ARCHIMEDES_C", "Archimedes D":"ARCHIMEDES_D",
                   "Luna 17": "LUNA17", "Luna 21":"LUNA21",
                   "Brewster":"BREWSTER",
                   "Le Monnier C":"LE_MONNIER_C", "Luther":"LUTHER",
                   "Bruce":"BRUCE", "Webb":"WEBB", "Peirce":"PEIRCE", 
                   "Lohrmann A":"LOHRMANN_A", "Damoiseau E":"DAMOISEAU_E",
                   "Milichius":"MILICHIUS", "Milichius A":"MILICHIUS_A",
                   "Mairan E":"MAIRAN_E", "Puiseux D":"PUISEUX_D",
                   "Nicolai A":"NICOLAI_A",
                   "North Limb":"NPOLE", "South Limb":"SPOLE", 
                   "East Limb":"ELIMB", "West Limb":"WLIMB"}

    self.long = {"Apollo 11":23.45864,
                "Moltke":24.19,
                "Torricelli C":26.02,
                "Blagg":1.5,
                "Messier":47.6,
                "Messier B":48.0,
                "Apollo 14":-17.49269,
                "Turner F":-14.05,
                "Fra Mauro B":-21.62,
                "Apollo 15":3.61476,
                "Nearby Knob":6.95,
                "Archimedes C":-1.56,
                "Archimedes D":-2.7,
                "Luna 17":-35.0338,
                "Luna 21":30.91310,
                "Brewster":34.7,
                "Le Monnier C":26.38,
                "Luther":24.15,
                "Bruce":0.4,
                "Webb":60.05,
                "Peirce":53.4,
                "Lohrmann A":-62.55,
                "Damoiseau E":-58.3,
                "Milichius":-30.17,
                "Milichius A":-32.00,
                "Mairan E":-37.17,
                "Puiseux D":-36.13,
                "Nicolai A":23.53,
                "North Limb":0.0,
                "South Limb":0.0,
                "East Limb":-90.0,
                "West Limb":90.0}

    self.lat = {"Apollo 11":0.69347,
                "Moltke": -0.85,
                "Torricelli C":-2.683,
                "Blagg": 1.2,
                "Messier":-1.85,
                "Messier B": -0.85,
                "Apollo 14":-3.62328,
                "Turner F":-1.63,
                "Fra Mauro B":-4.03,
                "Apollo 15":26.15515,
                "Nearby Knob":28.57,
                "Archimedes C":31.64,
                "Archimedes D":32.2,
                "Luna 17":38.3430,
                "Luna 21":25.85094,
                "Brewster":23.3,
                "Le Monnier C":22.32,
                "Luther": 33.25,
                "Bruce":1.1,
                "Webb":-0.95,
                "Peirce":18.2,
                "Lohrmann A":-0.7,
                "Damoiseau E":-5.25,
                "Milichius":10.03,
                "Milichius A":9.30,
                "Mairan E":37.82,
                "Puiseux D":-25.25,
                "Nicolai A":-42.32,
                "North Limb":90.0,
                "South Limb":-90.0,
                "East Limb":0.0,
                "West Limb":0.0}

