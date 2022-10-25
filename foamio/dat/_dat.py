from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
from foamio._common import REGEX_DIGIT


def __get_header_size(filepath: Path | str, comment: str = '#') -> int:
    """Get header size."""

    with open(filepath) as f:
        for index, line in enumerate(f):
            if not line.startswith(comment):
                return index - 1
    return 0


def __unnest_columns(dat: pd.DataFrame) -> pd.DataFrame:
    """Unnest non-scalar field values to components."""

    nested_columns: list = []
    for key, column_dtype in zip(dat, dat.dtypes):
        if (column_dtype == np.dtype('object')
                and re.match(rf'.*?{REGEX_DIGIT}', dat[key].iloc[-1])):

            dat[key] = dat[key].apply(lambda cell: np.array(
                cell.replace('(', '').replace(')', '').split(),
                dtype=float,
            ))

            pos, field = (
                dat.columns.to_list().index(key) + 1,
                np.array(dat[key].to_list()),
            )
            for component in range(field.shape[-1]):
                dat.insert(pos + component, f'{key}.{component}',
                           field[:, component])

            nested_columns.append(key)

    return dat.drop(nested_columns, axis='columns')


def read(filepath: Path | str,
         *,
         usecols: list | None = None,
         use_nth: int | None = None) -> pd.DataFrame:
    """Read OpenFOAM post-processing .dat file as pandas DataFrame.

    Args:
        filepath (Path | str): Path to .dat-file of directory
        with .dat-files.
        usecols (list[int], optional): Columns to read (starting with 1).
        Defaults to None.
        use_nth (int, optional): Read every n-th row. Defaults to None.

    Raises:
        ValueError: Raised when .dat-file path is invalid.

    Returns:
        pd.DataFrame: Converted to DataFrame .dat-file.
    """

    def _read(filepath: Path) -> pd.DataFrame:

        header_pos = __get_header_size(filepath)

        # Read .dat-file as pandas' DataFrame
        dat = pd.read_csv(
            filepath,
            sep='\t',
            header=header_pos,
            index_col=0,
            usecols=(usecols if usecols is None else ([0] + usecols)),
            skiprows=(lambda n: n > header_pos and n % use_nth
                      if not use_nth is None and use_nth >= 2 else None
                      ),  # type: ignore
        )

        # Drop '#' and trails spaces from column names
        dat.index.name = dat.index.name.replace('#', '').strip()
        dat.columns = dat.columns.str.strip()

        return __unnest_columns(dat)

    filepath = Path(filepath)

    # Merge all .dat-files in the direcotry into one dataframe
    if filepath.is_dir():
        filepaths = list(filepath.rglob('*.dat'))
        if len({fp.name for fp in filepaths}) != 1:
            raise ValueError(f'{filepath} is not valid')

        df = pd.concat([_read(dat_file) for dat_file in sorted(filepaths)])
        return df[~df.index.duplicated(keep='last')]

    return _read(filepath)
