import linecache
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd


def count_columns(filepath: Union[Path, str], sep: str, line_no: int = 1) -> int:
    """Count columns in a data-file by counting separators in a line."""

    line = linecache.getline(str(Path(filepath)), line_no)
    return line.count(sep) + line.count('\n')


def load_dat(filepath: Union[Path, str],
             usecols: list = None) -> pd.DataFrame:
    """Load OpenFOAM post-processing .dat file as pandas DataFrame."""

    def get_header_size(filepath: Union[Path, str], comment: str = '#') -> int:
        """Get header size."""

        with open(filepath) as f:
            for index, line in enumerate(f):
                if not line.startswith(comment):
                    return index - 1

    def unnest(dat: pd.DataFrame) -> pd.DataFrame:
        """Unnest non-scalar field values to components."""

        nested_columns: list = []
        for key, column_dtype in zip(dat, dat.dtypes):
            if column_dtype == np.dtype('object'):
                dat[key] = dat[key].apply(lambda cell: np.array(
                    cell.replace('(', '').replace(')', '').split(),
                    dtype=float))

                pos, field = (dat.columns.to_list().index(key) + 1,
                             np.array(dat[key].to_list()))
                for component_no in range(field.shape[-1]):
                    dat.insert(pos + component_no,
                               f'{key}.{component_no}',
                               field[:, component_no])

                nested_columns.append(key)

        return dat.drop(nested_columns, axis='columns')

    # Read .dat-file as pandas' DataFrame
    dat = pd.read_csv(filepath,
                      sep='\t',
                      header=get_header_size(filepath),
                      index_col=0,
                      usecols=usecols if usecols is None else ([0] + usecols))

    # Drop '#' and trails spaces from column names
    dat.index.name = dat.index.name.replace('#', '').strip()
    dat.columns = dat.columns.str.strip()

    return unnest(dat)


def load_xy(filepath: Union[Path, str],
            usecols: list = None) -> pd.DataFrame:
    """Load OpenFOAM post-processing .xy file as pandas DataFrame."""

    def field_components(field_name: str, components_count: int) -> list:
        if components_count <= 1:
            return [field_name]
        elif components_count == 3:
            components = 'xyz'
        elif components_count == 6:
            components = ['xx', 'yy', 'zz', 'xy', 'yz', 'zx']
        else:
            components = list(range(components_count))

        return [f'{field_name}.{component}' for component in components]

    # Get field names by splitting the filename
    field_names = Path(filepath).stem.split('_')

    columns_count = count_columns(filepath, sep='\t')

    # Get position of the first column with field value
    pos = 0
    if not (columns_count - 1) % len(field_names[1:]):
        pos = 1
    elif columns_count > 3 and not (columns_count - 3) % len(field_names[3:]):
        pos = 3

    # Constuct field names by appending components 
    components_count = (columns_count - pos) / len(field_names[pos:])
    names = field_components(field_names[0], pos)
    for field_name in field_names[pos:]:
        names += field_components(field_name, components_count)

    return pd.read_csv(filepath,
                       sep='\t',
                       index_col=0,
                       usecols=usecols if usecols is None else ([0] + usecols),
                       names=names)
