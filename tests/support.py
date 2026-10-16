from copy import deepcopy
from scripts.reviews.model import CRITERIA

TITLE = "[Review] McDonald's at 1 Main St, Springfield, IL, USA"
AUTHOR = {'login': 'traveler', 'id': 42, 'type': 'User'}
FIELDS = {
    'Big Mac recipe': 'Original standard local recipe',
    'Contribution type': 'New scored review',
    'Original review issue number': '_No response_',
    'Corrected review type': '_No response_',
    'Google Maps link': 'https://www.google.com/maps/place/McDonalds/@1,2,17z',
    'Visit date': '2025-01-02',
    'Order type': 'Dine-in',
    'Flavor and balance score': '4',
    'Texture score': '3',
    'Temperature score': '4',
    'Perceived freshness score': '3',
    'Assembly score': '5',
    'Overall experience': 'A good lunch.',
    'Confirmations': '- [X] I personally ate this Big Mac.\n- [X] It was the original standard local recipe: no extras, no ingredients removed, and no special edition.\n- [X] I have permission to share any photos included.',
}

def body(**overrides):
    fields = deepcopy(FIELDS)
    fields.update(overrides)
    return '\n\n'.join(f'### {key}\n\n{value}' for key, value in fields.items())

# Unselected optional dropdowns, as GitHub renders them for memory reviews.
NO_SCORES = {f'{criterion} score': 'None' for criterion in CRITERIA}
