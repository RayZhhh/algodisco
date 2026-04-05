"""Bundled seed sets for the moon lander task."""

TRAINING_SEEDS = [
    6, 9, 17, 29, 57,
    44, 18, 69, 26, 68,
    65, 23, 51, 93, 16,
    87, 92, 90, 22, 73,
    60, 10, 19, 97, 11,
    14, 99, 98, 8, 28,
    43, 56, 89, 15, 74,
]
TESTING_SEEDS = list(range(100, 150))

TRAINING_INSTANCES = {index: seed for index, seed in enumerate(TRAINING_SEEDS)}
TESTING_INSTANCES = {index: seed for index, seed in enumerate(TESTING_SEEDS)}
