from __future__ import annotations

from uuid import uuid4

import great_expectations as gx
import pandas as pd

class GXRuntime:
    def __init__(self) -> None:
        try:
            self.context = gx.get_context(mode="ephemeral")
        except TypeError:
            self.context = gx.get_context()
        self.datasource = self.context.data_sources.add_pandas(
            name=f"dq_pandas_runtime_{uuid4().hex}"
        )

    def batch(self, name: str, dataframe: pd.DataFrame):
        safe_name = "".join(ch if ch.isalnum() else "_" for ch in name)
        asset = self.datasource.add_dataframe_asset(name=safe_name)
        batch_definition = asset.add_batch_definition_whole_dataframe(
            f"{safe_name}_batch"
        )
        return batch_definition.get_batch(batch_parameters={"dataframe": dataframe})
