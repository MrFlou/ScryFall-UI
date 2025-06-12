import requests

class ScryfallAPI:
    BASE_URL = 'https://api.scryfall.com/cards/search'

    def search(self, query, page=1):
        params = {'q': query, 'page': page}
        resp = requests.get(self.BASE_URL, params=params)
        resp.raise_for_status()
        return resp.json()

    def filtered_search(self, query, collection_names):
        page, results = 1, []
        while True:
            data = self.search(query, page)
            for card in data.get('data', []):
                if card.get('name') in collection_names:
                    results.append(card)
            if not data.get('has_more'):
                break
            page += 1
        return results
