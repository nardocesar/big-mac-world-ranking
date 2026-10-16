from copy import deepcopy

AUTHOR = {'login': 'traveler', 'id': 42, 'type': 'User'}
FIELDS = {
    'Form version': 'big-mac-review-v1',
    'Contribution type': 'New scored review',
    'Original review issue number': '_No response_',
    'Corrected review type': '_No response_',
    'Google Maps link': 'https://www.google.com/maps/place/McDonalds/@1,2,17z',
    'Visit date': '2025-01-02',
    'Order type': 'Dine-in',
    'Flavor and balance score': '4',
    'Flavor and balance explanation': 'Balanced sauce.',
    'Texture score': '3',
    'Texture explanation': 'Soft bun and crisp lettuce.',
    'Temperature score': '4',
    'Temperature explanation': 'Warm enough.',
    'Perceived freshness score': '3',
    'Perceived freshness explanation': 'Fresh lettuce.',
    'Assembly score': '5',
    'Assembly explanation': 'Evenly distributed.',
    'Overall experience': 'A good lunch.',
    'Optional context': '_No response_',
    'Confirmations': '- [X] I personally ate this Big Mac.\n- [X] It was the original standard local recipe: no extras, no ingredients removed, and no special edition.\n- [X] I have permission to share any photos included.',
}

def body(**overrides):
    fields = deepcopy(FIELDS)
    fields.update(overrides)
    return '\n\n'.join(f'### {key}\n\n{value}' for key, value in fields.items())
