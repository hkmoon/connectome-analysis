"""Small topological tests for connalysis.network topology functions."""

import numpy as np
import pytest
from scipy import sparse


# ---------------------------------------------------------------------------
# Helpers – tiny hand-crafted adjacency matrices with known topology
# ---------------------------------------------------------------------------

def _chain_3():
    """3-node feedforward chain: 0→1→2 (one 1-simplex = 2-clique, no 2-simplex).

    Simplex counts (directed):
      dim-0 (vertices): 3
      dim-1 (edges / 1-simplices): 2
      dim-2 (2-simplices / triangles): 0
    """
    row = [0, 1]
    col = [1, 2]
    data = [1, 1]
    A = sparse.csr_matrix((data, (row, col)), shape=(3, 3))
    return A


def _directed_triangle():
    """Fully connected feedforward triple 0→1, 0→2, 1→2 = one directed 2-simplex.

    Simplex counts (directed):
      dim-0: 3
      dim-1: 3
      dim-2: 1
    """
    row = [0, 0, 1]
    col = [1, 2, 2]
    data = [1, 1, 1]
    A = sparse.csr_matrix((data, (row, col)), shape=(3, 3))
    return A


def _complete_directed_4():
    """All-to-all directed feedforward DAG on 4 nodes (one 3-simplex).

    Ordering: 0→1, 0→2, 0→3, 1→2, 1→3, 2→3
    Simplex counts (directed):
      dim-0: 4
      dim-1: 6
      dim-2: 4   (four directed 2-simplices)
      dim-3: 1   (one directed 3-simplex)
    """
    n = 4
    row, col = zip(*[(i, j) for i in range(n) for j in range(i + 1, n)])
    data = [1] * len(row)
    A = sparse.csr_matrix((data, (row, col)), shape=(n, n))
    return A


def _empty_graph(n=5):
    """No edges – only 0-simplices (vertices)."""
    return sparse.csr_matrix((n, n))


def _single_edge():
    """One directed edge 0→1."""
    A = sparse.csr_matrix(([1], ([0], [1])), shape=(4, 4))
    return A


# ---------------------------------------------------------------------------
# Tests – simplex_counts
# ---------------------------------------------------------------------------

class TestSimplexCounts:

    def test_empty_graph_has_only_vertices(self):
        """An edgeless graph has no simplices above dimension 0."""
        from connalysis.network import simplex_counts
        A = _empty_graph(5)
        counts = simplex_counts(A)
        # Only dim-0 (vertex count) should be non-zero
        assert counts[0] == 5
        assert all(counts[d] == 0 for d in counts.index if d > 0)

    def test_chain_no_2simplex(self):
        """A 3-node chain has edges but no directed 2-simplex."""
        from connalysis.network import simplex_counts
        A = _chain_3()
        counts = simplex_counts(A)
        assert counts[0] == 3
        assert counts[1] == 2
        # No closed feedforward triangle
        assert 2 not in counts.index or counts.get(2, 0) == 0

    def test_directed_triangle_one_2simplex(self):
        """Fully connected feedforward triple yields exactly one 2-simplex."""
        from connalysis.network import simplex_counts
        A = _directed_triangle()
        counts = simplex_counts(A)
        assert counts[0] == 3
        assert counts[1] == 3
        assert counts[2] == 1

    def test_complete_directed_4_counts(self):
        """All-to-all DAG on 4 nodes has the expected simplex counts."""
        from connalysis.network import simplex_counts
        A = _complete_directed_4()
        counts = simplex_counts(A)
        assert counts[0] == 4
        assert counts[1] == 6
        assert counts[2] == 4
        assert counts[3] == 1

    def test_return_type_is_series(self):
        """simplex_counts should return a pandas Series."""
        import pandas as pd
        from connalysis.network import simplex_counts
        A = _directed_triangle()
        counts = simplex_counts(A)
        assert isinstance(counts, pd.Series)

    def test_counts_nonnegative(self):
        """All simplex counts must be non-negative integers."""
        from connalysis.network import simplex_counts
        A = sparse.random(20, 20, density=0.15, random_state=42)
        A.setdiag(0)
        A.eliminate_zeros()
        counts = simplex_counts(A)
        assert (counts >= 0).all()

    def test_sparse_and_dense_equivalent(self):
        """Sparse and dense adjacency matrices should give identical counts."""
        from connalysis.network import simplex_counts
        A_sparse = _directed_triangle()
        A_dense = A_sparse.toarray()
        counts_sparse = simplex_counts(A_sparse)
        counts_dense = simplex_counts(A_dense)
        assert counts_sparse.equals(counts_dense)

    def test_single_edge(self):
        """A graph with a single edge has one 1-simplex and no higher ones."""
        from connalysis.network import simplex_counts
        A = _single_edge()
        counts = simplex_counts(A)
        assert counts[1] == 1
        assert 2 not in counts.index or counts.get(2, 0) == 0

    def test_diagonal_assertion(self):
        """Matrix with non-zero diagonal must raise an AssertionError."""
        from connalysis.network import simplex_counts
        A = _directed_triangle().toarray()
        A[0, 0] = 1  # introduce self-loop
        with pytest.raises(AssertionError):
            simplex_counts(sparse.csr_matrix(A))

    def test_non_square_assertion(self):
        """Non-square matrix must raise an AssertionError."""
        from connalysis.network import simplex_counts
        A = sparse.csr_matrix(np.ones((3, 4)))
        with pytest.raises(AssertionError):
            simplex_counts(A)

    def test_undirected_simplex_type(self):
        """Undirected simplex_type treats the graph as undirected."""
        from connalysis.network import simplex_counts
        # 3-node bidirectional triangle  ↔ clique = one undirected 2-simplex
        row = [0, 0, 1, 1, 2, 2]
        col = [1, 2, 0, 2, 0, 1]
        A = sparse.csr_matrix(([1]*6, (row, col)), shape=(3, 3))
        counts = simplex_counts(A, simplex_type='undirected')
        assert counts[2] >= 1

    def test_max_dim_limits_output(self):
        """max_dim parameter should cap the dimension of returned counts."""
        from connalysis.network import simplex_counts
        A = _complete_directed_4()
        counts = simplex_counts(A, max_dim=2)
        assert 3 not in counts.index or counts.get(3, 0) == 0


# ---------------------------------------------------------------------------
# Tests – edge_participation
# ---------------------------------------------------------------------------

class TestEdgeParticipation:

    def test_returns_dataframe(self):
        """edge_participation should return a pandas DataFrame."""
        import pandas as pd
        from connalysis.network import edge_participation
        A = _directed_triangle()
        ep = edge_participation(A)
        assert isinstance(ep, pd.DataFrame)

    def test_number_of_rows_equals_edge_count(self):
        """One row per edge in the adjacency matrix."""
        from connalysis.network import edge_participation
        A = _directed_triangle()
        ep = edge_participation(A)
        nnz = A.nnz
        assert len(ep) == nnz

    def test_single_edge_not_in_any_simplex(self):
        """An isolated edge not part of any 2-simplex has zero participation above dim 1."""
        from connalysis.network import edge_participation
        A = _single_edge()
        ep = edge_participation(A)
        # The single edge participates in one 1-simplex (itself) but no 2-simplices
        high_dim_cols = [c for c in ep.columns if c >= 2]
        if high_dim_cols:
            assert (ep[high_dim_cols] == 0).all().all()

    def test_triangle_edge_participation(self):
        """In a directed 2-simplex every edge participates in at least one 2-simplex."""
        from connalysis.network import edge_participation
        A = _directed_triangle()
        ep = edge_participation(A)
        # Column 2 should exist and every edge participates in exactly 1 dim-2 simplex
        assert 2 in ep.columns
        assert (ep[2] == 1).all()

    def test_nonnegative_values(self):
        """All participation counts must be non-negative."""
        from connalysis.network import edge_participation
        A = sparse.random(20, 20, density=0.15, random_state=0)
        A.setdiag(0)
        A.eliminate_zeros()
        ep = edge_participation(A)
        assert (ep >= 0).all().all()

    def test_empty_graph_empty_dataframe(self):
        """A graph without edges yields an empty participation table."""
        from connalysis.network import edge_participation
        A = _empty_graph(5)
        ep = edge_participation(A)
        assert len(ep) == 0

    def test_diagonal_assertion(self):
        """Non-zero diagonal must raise AssertionError."""
        from connalysis.network import edge_participation
        A = _directed_triangle().toarray().astype(float)
        A[1, 1] = 1.0
        with pytest.raises(AssertionError):
            edge_participation(sparse.csr_matrix(A))

    def test_return_simplex_counts_flag(self):
        """return_simplex_counts=True should return a tuple (DataFrame, cell_counts)."""
        from connalysis.network import edge_participation
        A = _directed_triangle()
        result = edge_participation(A, return_simplex_counts=True)
        assert isinstance(result, tuple)
        ep, cell_counts = result
        import pandas as pd
        assert isinstance(ep, pd.DataFrame)

    def test_complete_4_node_participation_at_dim3(self):
        """In a complete directed 4-simplex, edges must appear in dim-3 simplices."""
        from connalysis.network import edge_participation
        A = _complete_directed_4()
        ep = edge_participation(A)
        # At least one edge participates in a dim-3 simplex
        assert 3 in ep.columns
        assert ep[3].sum() > 0

    def test_max_dim_limits_columns(self):
        """max_dim parameter should cap the column dimensions returned."""
        from connalysis.network import edge_participation
        A = _complete_directed_4()
        ep = edge_participation(A, max_dim=2)
        assert 3 not in ep.columns