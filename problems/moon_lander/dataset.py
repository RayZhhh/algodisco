"""Bundled seed sets for the moon lander task."""

TRAINING_SEEDS = [42, 520, 1231, 114, 886]
TESTING_SEEDS = list(range(100, 150))

TRAINING_INSTANCES = {index: seed for index, seed in enumerate(TRAINING_SEEDS)}
TESTING_INSTANCES = {index: seed for index, seed in enumerate(TESTING_SEEDS)}
