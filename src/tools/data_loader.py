from functools import lru_cache
from pathlib import Path
from typing import Optional

import pandas as pd

from src.config import DATA_DIR


def _load_csv(name: str, data_dir: Optional[Path] = None) -> pd.DataFrame:
    directory = data_dir or DATA_DIR
    path = directory / name
    return pd.read_csv(path)


@lru_cache(maxsize=None)
def finance_fact(data_dir: Optional[Path] = None) -> pd.DataFrame:
    return _load_csv("finance_fact.csv", data_dir)


@lru_cache(maxsize=None)
def orders_fact(data_dir: Optional[Path] = None) -> pd.DataFrame:
    return _load_csv("orders_fact.csv", data_dir)


@lru_cache(maxsize=None)
def supply_fact(data_dir: Optional[Path] = None) -> pd.DataFrame:
    return _load_csv("supply_fact.csv", data_dir)


@lru_cache(maxsize=None)
def shipments_fact(data_dir: Optional[Path] = None) -> pd.DataFrame:
    return _load_csv("shipments_fact.csv", data_dir)


@lru_cache(maxsize=None)
def fx_fact(data_dir: Optional[Path] = None) -> pd.DataFrame:
    return _load_csv("fx_fact.csv", data_dir)


@lru_cache(maxsize=None)
def events_log(data_dir: Optional[Path] = None) -> pd.DataFrame:
    return _load_csv("events_log.csv", data_dir)


class DataRepository:
    """Thin wrapper around cached loaders for convenience and swapping storage later."""

    def __init__(self, data_dir: Optional[Path] = None) -> None:
        self.data_dir = data_dir

    def finance(self) -> pd.DataFrame:
        return finance_fact(self.data_dir).copy()

    def orders(self) -> pd.DataFrame:
        return orders_fact(self.data_dir).copy()

    def supply(self) -> pd.DataFrame:
        return supply_fact(self.data_dir).copy()

    def shipments(self) -> pd.DataFrame:
        return shipments_fact(self.data_dir).copy()

    def fx(self) -> pd.DataFrame:
        return fx_fact(self.data_dir).copy()

    def events(self) -> pd.DataFrame:
        return events_log(self.data_dir).copy()

    def shipments(self) -> pd.DataFrame:
        return shipments_fact(self.data_dir).copy()
