"""Bundled evaluation seeds for the car racing task."""

# Match the CarRacing seed split described in the MLES paper setup:
# four training tracks plus an unseen test range from 0 through 10.
TRAINING_SEEDS = [40, 1231, 516, 413]
TESTING_SEEDS = list(range(11))

# Expose dictionary forms because they are convenient for per-instance metrics
# and mirror how the upstream task represented instance collections.
TRAINING_INSTANCES = {index: seed for index, seed in enumerate(TRAINING_SEEDS)}
TESTING_INSTANCES = {index: seed for index, seed in enumerate(TESTING_SEEDS)}
