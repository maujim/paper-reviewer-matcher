import numpy as np
import pandas as pd
from fuzzywuzzy import fuzz
from tqdm.auto import tqdm
from .lp import linprog
from .affinity import create_lp_matrix, create_assignment

__all__ = ["perform_mindmatch"]


def compute_conflicts(df: pd.DataFrame, ratio: int = 85, sep: str = ";"):
    """
    Compute conflict for a given dataframe

    Parameters
    ==========
    df: pd.Dataframe, a dataframe which have a column "conflicts"
        where each row has
        scientist names with separator (default as semicolon ;)
    ratio: int, Fuzzy matching ratio, 100 mean exact match, 85 allow some errors
    sep: str, a separator
    """
    cois = []
    for i, r in tqdm(df.iterrows()):
        exclude_list = r['conflicts'].split(sep)
        for j, r_ in df.iterrows():
            if max([fuzz.ratio(r_['fullname'], n) for n in exclude_list]) >= ratio:
                cois.append([i, j])
                cois.append([j, i])
    return cois


def perform_mindmatch(
    A: np.array, n_trim: int = None,
    n_match: int = 6, cois: list = None
):
    """
    Perform mindmatching with a given matrix A,
    trimming of n_trim (reduce problem size),
    matching between n_match people
    """
    # setting distance in the diagonal
    A[np.arange(len(A)), np.arange(len(A))] = -1000 

    # if conflict of interest (COIs) is available, add to the matrix
    cois = [(c1, c2) for (c1, c2) in cois
            if c1 <= len(A) and c2 <= len(A)] # make sure a given cois is in range
    A[np.array(cois, dtype=int)] = -1000

    # trimming affinity matrix to reduce the problem size
    if n_trim != 0:
        A_trim = []
        for r in range(len(A)):
            a = A[r, :]
            a[np.argsort(a)[0:n_trim]] = 0
            A_trim.append(a)
        A_trim = np.vstack(A_trim)
    else:
        A_trim = A

    # solving matching problem
    print('Solving a matching problem...')
    v, K, d = create_lp_matrix(A_trim, 
                               min_reviewers_per_paper=n_match, max_reviewers_per_paper=n_match,
                               min_papers_per_reviewer=n_match, max_papers_per_reviewer=n_match)
    x_sol = linprog(v, K, d)['x']
    b = create_assignment(x_sol, A_trim)

    if (b.sum() == 0):
        print('Seems like the problem does not converge, try reducing <n_trim> but not too low!')
    else:
        print('Successfully assigned all the match!')
    return b
