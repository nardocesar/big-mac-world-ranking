from copy import deepcopy

TITLE = "[Review] McDonald's at 1 Main St, Springfield, IL, USA"
AUTHOR = {'login': 'traveler', 'id': 42, 'type': 'User'}
FIELDS = {
    'Big Mac recipe': 'Original standard local recipe',
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
    fields = {key: value for key, value in fields.items() if value is not None}
    return '\n\n'.join(f'### {key}\n\n{value}' for key, value in fields.items())


def correction(original='123', **overrides):
    """Body of the separate Correct a review form."""
    return body(**{'Original review issue number': original, **overrides})
