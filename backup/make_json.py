import json
import random

def generate_large_alliance_json(filepath="allianz.json"):
    members = []
    
    # 1. Die ersten 10 Mitglieder als R4 generieren
    for i in range(1, 11):
        # Zufällige, realistische R4-Power zwischen 70.000.000 und 95.000.000
        power = random.randint(70, 95) * 1_000_000
        members.append({
            "name": f"Mitglied {i}",
            "rang": "R4",
            "power": power,
            "partner": None
        })
        
    # 2. Die restlichen 81 Mitglieder (11 bis 91) als R1 generieren
    for i in range(11, 92):
        # Zufällige R1-Power zwischen 15.000.000 und 45.000.000
        power = random.randint(15, 45) * 1_000_000
        members.append({
            "name": f"Mitglied {i}",
            "rang": "R1",
            "power": power,
            "partner": None
        })
        
    # Die Daten sauber in die allianz.json schreiben
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(members, f, indent=2, ensure_ascii=False)
        
    print(f"Erfolg! '{filepath}' wurde mit {len(members)} Mitgliedern erfolgreich erstellt.")

if __name__ == "__main__":
    generate_large_alliance_json()