import marimo

__generated_with = "0.18.0"
app = marimo.App(
    width="medium",
    app_title="Strength Viewer",
    auto_download=["html"],
)


@app.cell(hide_code=True)
def _(df, fig, mo, ui_selected_second_dof, ui_selected_study):
    mo.vstack([ui_selected_study,ui_selected_second_dof, mo.ui.plotly(fig), mo.ui.table(df, page_size=5)])
    return


@app.cell
def _():
    import marimo as mo
    import plotly.express as px
    import plotly.graph_objects as go
    import polars as pd
    import polars as pl

    df_full = pd.read_parquet("joint-strength-full.parquet")
    #df_full
    return df_full, mo, pd, pl, px


@app.cell
def _(df_full, mo):
    ui_selected_study = mo.ui.dropdown(
        options=df_full["measureObject"].unique().sort().to_list(),
        value=df_full["measureObject"].unique().sort().to_list()[0],
        label="Select Joint Measurement:",
    )
    return (ui_selected_study,)


@app.cell
def _(df_study, mo):
    ui_selected_second_dof = mo.ui.dropdown(
        options=df_study["measureSecondDoF"].unique().sort().to_list(),
        value=0,
        label=f"Second DOF: {df_study["secondaryDoF"].first()}",
    )
    ui_selected_second_dof = mo.ui.dropdown(
        options=df_study["measureSecondDoF"].unique().sort().to_list(),
        value=0,
        label=f"Second DOF: {df_study["secondaryDoF"].first()}",
    )
    return (ui_selected_second_dof,)


@app.cell(hide_code=True)
def _(df_full, pl, ui_selected_study):
    df_study = df_full.filter(pl.col("measureObject") == ui_selected_study.value)
    return (df_study,)


@app.cell
def _(df_study, pl, ui_selected_second_dof):
    df = df_study.filter(pl.col("measureSecondDoF") == ui_selected_second_dof.value)
    #df
    return (df,)


@app.cell
def _(df, px):
    fig = px.line(df, x="measurePrimaryDoF", y="measureValue", color="AnyBodyMuscleType")

    fig.update_layout(
        xaxis_title=df["primaryDoF"].unique()[0],
        yaxis_title="Strength",
        title=f"{df['measureObject'].first()} Strength",
    );
    return (fig,)


@app.cell
def _(df_measured_all):
    df_measured_all

    return


@app.cell
def _(mo, pd):
    df_measured_all = pd.read_parquet("convert-matlab-data/isometric.parquet")
    ui_selected_measured = mo.ui.dropdown(
        options=df_measured_all["measureObject"].unique().sort().to_list(),
        value=df_measured_all["measureObject"].first(),
        label="Select Joint Measurement:",
    );
    #ui_selected_measured
    #df_measured_all
    return df_measured_all, ui_selected_measured


@app.cell
def _(df_measured_all, pl, ui_selected_measured):
    df_measured = df_measured_all.filter(pl.col("measureObject")==ui_selected_measured.value)
    #df_measured
    return


if __name__ == "__main__":
    app.run()
