import sys
sys.path.append('C:/SideProjects-Git/ScryFall-UI')
from core.scryfall_api import ScryfallAPI

api = ScryfallAPI()
collection_id = 550191  # Example public collection ID

print(f"Attempting to fetch Archidekt collection ID: {collection_id}")
cards = api.get_archidekt_collection_from_api(collection_id)

if cards:
    print(f"Successfully retrieved {len(cards)} cards.")
    print("Sample cards:")
    for i, card in enumerate(cards[:5]):
        print(f"- {card}")
else:
    print("Failed to retrieve any card names or collection is empty.")