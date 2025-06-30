import requests
import json
import csv
import io

class ScryfallAPI:
    BASE_URL = 'https://api.scryfall.com/cards/search'
    ARCHIDEKT_BASE_URL = 'https://archidekt.com'

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

    def get_archidekt_collection_from_api(self, collection_id):
        all_cards = []
        page = 1
        has_more = True

        while has_more:
            try:
                json_response = self._fetch_archidekt_page(collection_id, page)
                csv_content = json_response.get('content')
                has_more = json_response.get('moreContent', False)

                if not csv_content:
                    break

                cards = self._parse_archidekt_csv(csv_content)
                all_cards.extend(cards)
                
                print(f"Fetched page {page}. Total cards so far: {len(all_cards)}")
                page += 1

            except requests.exceptions.RequestException as e:
                print(f"Error fetching Archidekt collection from API on page {page}: {e}")
                return []
        
        return all_cards

    def _fetch_archidekt_page(self, collection_id, page):
        url = f"{self.ARCHIDEKT_BASE_URL}/api/collection/export/v2/{collection_id}/"
        headers = {
            "accept": "application/json",
            "content-type": "application/json"
        }
        payload = {
            "fields": [
                "quantity", "card__oracleCard__name", "modifier", "condition",
                "createdAt", "language", "purchasePrice", "tags",
                "card__edition__editionname", "card__edition__editioncode",
                "card__multiverseid", "card__uid", "card__collectorNumber"
            ],
            "page": page,
            "game": 1,
            "pageSize": 10000
        }
        resp = requests.post(url, headers=headers, data=json.dumps(payload))
        resp.raise_for_status()
        return resp.json()

    def _parse_archidekt_csv(self, csv_content):
        csvfile = io.StringIO(csv_content)
        reader = csv.DictReader(csvfile)
        cards = []
        for row in reader:
            cards.append(row)
        return cards
