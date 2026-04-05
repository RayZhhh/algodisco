"""Bundled evaluation seeds for the car racing task."""

# Keep the default seed split close to the original MLES example. The evaluator
# uses the training seeds by default so task examples stay fast and deterministic.
TRAINING_SEEDS = [1]
TESTING_SEEDS = list(range(10, 20))

# Expose dictionary forms because they are convenient for per-instance metrics
# and mirror how the upstream task represented instance collections.
TRAINING_INSTANCES = {index: seed for index, seed in enumerate(TRAINING_SEEDS)}
TESTING_INSTANCES = {index: seed for index, seed in enumerate(TESTING_SEEDS)}
