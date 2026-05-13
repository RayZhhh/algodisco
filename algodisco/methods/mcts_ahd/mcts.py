# Copyright (c) 2026 Rui Zhang
# Licensed under the MIT license.

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from algodisco.base.algo import AlgoProto


@dataclass
class MCTSNode:
    """One node in the MCTS-AHD search tree.

    Attributes:
        algo: The algorithm candidate represented by this node. The root node
            stores ``None``.
        parent: Parent node in the tree.
        depth: Depth from the root. The root has depth 0.
        visits: Number of visits accumulated through backpropagation.
        q_value: Backpropagated quality estimate used by UCT.
        children: Explicit child nodes.
        subtree: All nodes that belong to the same branch rooted at a direct
            child of the root. This is mainly used by the ``e1`` operator, which
            samples one representative from each root branch.
    """

    algo: Optional[AlgoProto]
    parent: Optional["MCTSNode"] = None
    depth: int = 0
    visits: int = 0
    q_value: float = 0.0
    children: List["MCTSNode"] = field(default_factory=list)
    subtree: List["MCTSNode"] = field(default_factory=list)

    def add_child(self, child: "MCTSNode") -> None:
        """Attach a child node to the current node."""
        self.children.append(child)

    @property
    def is_root(self) -> bool:
        """Return ``True`` if this node is the tree root."""
        return self.parent is None

    @property
    def score(self) -> Optional[float]:
        """Expose the candidate score stored at this node."""
        if self.algo is None:
            return None
        return self.algo.score

    @property
    def program(self) -> str:
        """Expose the program text stored at this node."""
        if self.algo is None:
            return "Root"
        return str(self.algo.program)

    def root_branch(self) -> Optional["MCTSNode"]:
        """Return the direct child of the root that owns this node's branch."""
        node = self
        while node.parent is not None and node.parent.parent is not None:
            node = node.parent
        if node.parent is None:
            return None
        return node

    def path_from_root(self) -> List["MCTSNode"]:
        """Return the node path from root to the current node."""
        path: List[MCTSNode] = []
        node: Optional[MCTSNode] = self
        while node is not None:
            path.append(node)
            node = node.parent
        path.reverse()
        return path


class MCTSTree:
    """Lightweight MCTS container specialized for MCTS-AHD."""

    def __init__(
        self,
        *,
        alpha: float,
        lambda_0: float,
        max_depth: int,
    ):
        """Create an empty search tree with one synthetic root node."""
        self.alpha = alpha
        self.lambda_0 = lambda_0
        self.max_depth = max_depth
        self.root = MCTSNode(algo=None, depth=0, visits=1, q_value=0.0)

        # These ranges are used for score normalization in UCT.
        self.q_min = 0.0
        self.q_max = 0.0
        self.rank_list: List[float] = []

    def add_root_child(self, algo: AlgoProto) -> MCTSNode:
        """Create a root child from one initialized algorithm."""
        node = MCTSNode(
            algo=algo,
            parent=self.root,
            depth=1,
            visits=1,
            q_value=float(algo.score),
        )
        node.subtree.append(node)
        self.root.add_child(node)
        # Root children are also full-fledged search nodes, so they immediately
        # contribute score information to the root via backpropagation.
        self.backpropagate(node)
        return node

    def attach_child(self, parent: MCTSNode, algo: AlgoProto) -> MCTSNode:
        """Attach a newly accepted candidate under ``parent`` and backpropagate."""
        child = MCTSNode(
            algo=algo,
            parent=parent,
            depth=parent.depth + 1,
            visits=1,
            q_value=float(algo.score),
        )
        parent.add_child(child)

        # Each root branch maintains a flat subtree cache so the e1 operator can
        # cheaply sample one representative per top-level branch.
        branch = child.root_branch()
        if branch is not None:
            branch.subtree.append(child)

        self.backpropagate(child)
        return child

    def backpropagate(self, node: MCTSNode) -> None:
        """Propagate one node's score information toward the root."""
        if node.score is None:
            return

        # `rank_list` is mainly a lightweight diagnostic artifact for logging;
        # it records which terminal scores have ever appeared in the tree.
        if node.q_value not in self.rank_list:
            self.rank_list.append(node.q_value)
            self.rank_list.sort()

        self.q_min = min(self.q_min, node.q_value)
        self.q_max = max(self.q_max, node.q_value)

        current = node.parent
        while current is not None:
            current.visits += 1
            if current.children:
                # This tree stores a max-style backed-up value rather than an
                # average return because the method is searching for the best
                # discovered heuristic, not estimating expected rollout reward.
                current.q_value = max(child.q_value for child in current.children)
            current = current.parent

    def uct(self, node: MCTSNode, eval_remain_ratio: float) -> float:
        """Compute the UCT score used during tree traversal.

        Args:
            node: Candidate child node under evaluation.
            eval_remain_ratio: Remaining search budget ratio in ``[0, 1]``.

        Returns:
            The UCT score for the node.
        """
        if node.visits <= 0:
            return float("inf")

        if self.q_max > self.q_min:
            normalized_q = (node.q_value - self.q_min) / (self.q_max - self.q_min)
        else:
            normalized_q = 0.0

        parent_visits = node.parent.visits if node.parent is not None else 1
        exploration = self.lambda_0 * eval_remain_ratio * math.sqrt(
            math.log(parent_visits + 1.0) / node.visits
        )
        return normalized_q + exploration

    def should_expand_before_descending(self, node: MCTSNode) -> bool:
        """Return whether the node should try adding a new child before descent."""
        # The branching target grows sublinearly with visits, which gives busy
        # nodes room to expand without forcing every visit to create a child.
        target_branching = max(1, int(node.visits**self.alpha))
        return target_branching > len(node.children)

    def num_nodes(self) -> int:
        """Return the total number of explicit nodes currently in the tree."""
        count = 1
        queue = list(self.root.children)
        while queue:
            node = queue.pop()
            count += 1
            queue.extend(node.children)
        return count

    def to_dict(self) -> Dict[str, Any]:
        """Serialize a compact summary of the current tree state."""
        branch_sizes = [len(child.subtree) for child in self.root.children]
        return {
            "num_nodes": self.num_nodes(),
            "num_root_children": len(self.root.children),
            "rank_list": list(self.rank_list),
            "branch_sizes": branch_sizes,
        }
