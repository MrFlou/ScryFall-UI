from pyrchidekt.api import getDeckById

collection_id = 550191

try:
    deck = getDeckById(collection_id)
    if deck:
        print(f"Successfully retrieved deck: {deck.name}")
        print(f"Deck ID: {deck.id}")
        card_names = set()
        for category in deck.categories:
            for card in category.cards:
                if card.card and card.card.oracle_card and card.card.oracle_card.name:
                    card_names.add(card.card.oracle_card.name)
        print(f"Number of cards: {len(card_names)}")
    else:
        print(f"Could not retrieve deck with ID: {collection_id}. Deck object is None.")
except Exception as e:
    print(f"An error occurred: {e}")
