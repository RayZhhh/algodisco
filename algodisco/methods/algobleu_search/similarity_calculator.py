# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

import time

import numpy as np

from algodisco.base.algo import AlgoProto
from algodisco.third_party.codebleu.syntax_match import calc_syntax_match
from algodisco.third_party.codebleu.dataflow_match import calc_dataflow_match
from algodisco.third_party.codebleu.utils import get_tree_sitter_language


class AlgoSimCalculator:
    """Calculates the similarity between two AlgoProto instances.

    The total similarity is a weighted sum of different similarity components:
    AST similarity, embedding similarity, and behavioral similarity.
    Weights for these components can be set during initialization.
    """

    def calculate_sim(
        self,
        algo1: AlgoProto,
        algo2: AlgoProto,
        weights: dict[str, float] = None,
    ) -> tuple[float, dict[str, float]]:
        """Calculates the total weighted similarity between two AlgoProto instances.

        The total similarity is a weighted sum of AST, embedding, and behavioral similarities.

        Args:
            algo1: The first AlgoProto instance.
            algo2: The second AlgoProto instance.
            weights: A dictionary of weights for different similarity components.
                     Expected keys: "ast", "embedding", "behavioral".
                     If None, defaults to equal weights of 1.0 (normalized).

        Returns:
            A tuple containing:
            - float: The total weighted similarity score between algo1 and algo2.
            - dict: A dictionary containing the execution time (in seconds) for each similarity component.
        """
        if weights is None:
            weights = {
                "ast": 1.0,
                "embedding": 1.0,
                "behavioral": 1.0,
            }

        # Normalize weights
        total_weight = sum(weights.values())
        normalized_weights = {}
        if total_weight > 0:
            for key, val in weights.items():
                normalized_weights[key] = val / total_weight
        else:
            return 0.0, {}

        sim_scores = {
            "ast": lambda a, b: self._ast_dfg_similarity(a, b),
            "embedding": lambda a, b: self._embedding_similarity(a, b),
            "behavioral": lambda a, b: self._behavioral_similarity(a, b),
        }

        total_sim = 0.0
        timings = {}
        for sim_type, sim_func in sim_scores.items():
            weight = normalized_weights.get(sim_type, 0)
            if weight > 0:
                start_time = time.time()
                score = sim_func(algo1, algo2)
                end_time = time.time()
                timings[sim_type] = end_time - start_time
                total_sim += weight * score

        return total_sim, timings

    def _ast_dfg_similarity(self, algo1: AlgoProto, algo2: AlgoProto) -> float:
        return self._ast_similarity(algo1, algo2)

    def _ast_similarity(self, algo1: AlgoProto, algo2: AlgoProto) -> float:
        """Calculates the Abstract Syntax Tree (AST) similarity between two AlgoProto instances.

        This method uses the `codebleu.syntax_match.calc_syntax_match` function
        to compare the ASTs of the program representations.

        Args:
            algo1: The first AlgoProto instance.
            algo2: The second AlgoProto instance.

        Returns:
            A float representing the AST similarity score, averaged for both directions.
        """
        assert algo1.language == algo2.language
        language = algo1.language
        sim1 = calc_syntax_match([str(algo1.program)], str(algo2.program), language)
        sim2 = calc_syntax_match([str(algo2.program)], str(algo1.program), language)
        return (sim1 + sim2) / 2

    def _dfg_similarity(self, algo1: AlgoProto, algo2: AlgoProto) -> float:
        assert algo1.language == algo2.language
        language = algo1.language
        ts_lang = get_tree_sitter_language(language)  # Tree sitter language
        sim1 = calc_dataflow_match(
            [str(algo1.program)], str(algo2.program), language, ts_lang
        )
        sim2 = calc_dataflow_match(
            [str(algo2.program)], str(algo1.program), language, ts_lang
        )
        return (sim1 + sim2) / 2

    def _embedding_similarity(self, algo1: AlgoProto, algo2: AlgoProto) -> float:
        """Calculates the embedding similarity (cosine similarity) between two AlgoProto instances.

        This method computes the cosine similarity between the embeddings of algo1 and algo2.

        Args:
            algo1: The first AlgoProto instance.
            algo2: The second AlgoProto instance.

        Returns:
            A float representing the embedding similarity score.
            Returns 0.0 if either embedding is a zero vector.
        """
        embedding1 = algo1["embedding"]
        embedding2 = algo2["embedding"]

        # Normalize the vector and calculate cosine similarity
        dot_product = np.dot(embedding1, embedding2)
        norm_a = np.linalg.norm(embedding1)
        norm_b = np.linalg.norm(embedding2)

        # Return 0.0 if either vector is a zero vector
        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def _behavioral_similarity(self, algo1: AlgoProto, algo2: AlgoProto) -> float:
        """Placeholder for calculating behavioral similarity.

        Args:
            algo1: The first AlgoProto instance.
            algo2: The second AlgoProto instance.

        Returns:
            Currently returns 0.0, as this component is not yet implemented.
        """
        return 0.0
