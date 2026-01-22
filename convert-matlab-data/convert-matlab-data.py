import marimo

__generated_with = "0.16.1"
app = marimo.App(width="medium")

with app.setup:
    # Initializimport marimo as mo

    import marimo as mo
    import scipy as sp
    import polars as pl
    import numpy as np


@app.cell
def _():
    mat = sp.io.loadmat("S3_Datasets.mat")
    mat_momentarm = mat["dataset_momentArm"][0]
    mat_isokinetic = mat["dataset_isokinetic"][0]
    mat_isometric_passive = mat["dataset_isometric_passive"][0]
    return (mat,)


@app.cell
def _(mat):
    def read_data(name) -> pl.DataFrame():
        if name == "momentarm":
            exceldata = pl.read_excel("S2_Metadata_Catalog.xlsx", sheet_name="Moment Arm")
            matlabdata = mat["dataset_momentArm"][0]
        elif name == "isometric":
            exceldata = pl.read_excel("S2_Metadata_Catalog.xlsx", sheet_name="Isometric&Passive")
            matlabdata = mat["dataset_isometric_passive"][0]
        elif name == "isokinetic":
            exceldata = pl.read_excel("S2_Metadata_Catalog.xlsx", sheet_name="Isokinetic")
            matlabdata = mat["dataset_isokinetic"][0]

        extra_data = exceldata.select(
            pl.col("No.").cast(pl.String).alias("id"),
            pl.col("Subject Note").alias("subjectNote"),
            pl.col("Group Note").alias("groupNote"),
            pl.col("Data Note").alias("dataNote"),
            pl.col("DOI").alias("doi"),
        )
        _schema = {
            "id": pl.String,
            "measurement": pl.String,
            "reference": pl.String,
            "subject": pl.String,
            "subjectType": pl.String,
            "subjectHeight": pl.Float64,
            "subjectWeight": pl.Float64,
            "subjectNote": pl.String,
            "groupNote": pl.String,
            "dataNote": pl.String,
            "doi": pl.String,
            "measureObject": pl.String,
            "measureType": pl.String,
            "primaryDoF": pl.String,
            "secondaryDoF": pl.String,
            "tertiaryDoF": pl.String,
            "measureValue": pl.Float64,
            "measurePrimaryDoF": pl.Float64,
            "measureSecondDoF": pl.Float64,
            "measureTertiaryDoF": pl.Float64,
        }
        df_data = pl.DataFrame(schema=_schema, strict=True)
        for index, entry in enumerate(matlabdata):
            entry_dict = {}
            measure_value = None
            for col in _schema:
                if col in extra_data.columns:
                    value = extra_data[index, col]
                elif col not in entry.dtype.names:
                    continue
                else:
                    value = entry[col][0]
                    if isinstance(value, str):
                        if _schema[col] == pl.Float64:
                            value = float("nan")
                    elif _schema[col] == pl.String:
                        value = None
                    elif col == "measureValue":
                        measure_value = value[0]
                        continue
                entry_dict[col] = value
            for i in range(measure_value.shape[1]):
                entry_dict["measurePrimaryDoF"] = measure_value[0, i]
                entry_dict["measureSecondDoF"] = measure_value[1, i]
                if len(measure_value) == 4:
                    entry_dict["measureTertiaryDoF"] = measure_value[2, i]
                    debug = entry
                else:
                    entry_dict["measureTertiaryDoF"] = float("Nan")
                entry_dict["measureValue"] = measure_value[-1, i]
                df_data = df_data.vstack(pl.DataFrame(entry_dict, schema=_schema, strict=True))
        df_data.write_parquet(f"{name}.parquet")
        return df_data.rechunk()
    return (read_data,)


@app.cell
def _(read_data):
    read_data("momentarm")
    return


@app.cell
def _(read_data):
    read_data("isokinetic")
    return


@app.cell
def _(read_data):
    read_data("isometric")
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
