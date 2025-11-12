
import glob
import itertools
import os

import anypytools.macro_commands as mc
import numpy as np
import polars as pl
import typer
from anypytools import AnyPyProcess

app = typer.Typer(no_args_is_help=True, add_completion=False)

# Maps the DOF name to its description/axis-label and sign convention compared to AMS
dof_map = {
    "HipFlexion": ("Hip extension(-)/flexion(+)", 1),
    "HipAbduction": ("Hip abduction(-)/adduction(+)", -1),
    "HipExternalRotation": ("Hip external(-)/internal(+) rotation", -1),
    "KneeFlexion": ("Knee extension(-)/flexion(+)", 1),
    "AnklePlantarFlexion": ("Ankle plantar(-)/dorsi(+)flexion", -1),
    "SubtalarEversion": ("Ankle eversion(-)/inversion(+)", -1),
}

# Maps the AnyBody strength study name to the columns in the output
study_map = {
    "HipFlexion": "Hip flexion",
    "HipExtension": "Hip extension",
    "HipAbduction": "Hip abduction",
    "HipAdduction": "Hip adduction",
    "HipExternalRotation": "Hip external rotation",
    "HipInternalRotation": "Hip internal rotation",
    "KneeFlexion": "Knee flexion",
    "KneeExtension": "Knee extension",
    "AnklePlantarFlexion": "Ankle plantarflexion",
    "AnkleDorsiFlexion": "Ankle dorsiflexion",
    "SubTalarEversion": "Ankle eversion",
    "SubTalarInversion": "Ankle inversion",
}

# This plan for the batch simulation defines for each study (key) which is the primary and secondary DOF (value)
simulation_plan: dict[str, tuple[str, str]] = {
    "AnkleDorsiFlexion": ("AnklePlantarFlexion", "KneeFlexion"),
    "AnklePlantarFlexion": ("AnklePlantarFlexion", "KneeFlexion"),
    "SubTalarEversion": ("SubtalarEversion", "AnklePlantarFlexion"),
    "SubTalarInversion": ("SubtalarEversion", "AnklePlantarFlexion"),
    "HipAbduction": ("HipAbduction", "HipFlexion"),
    "HipAdduction": ("HipAbduction", "HipFlexion"),
    "HipExtension": ("HipFlexion", "KneeFlexion"),
    "HipFlexion": ("HipFlexion", "KneeFlexion"),
    "HipExternalRotation": ("HipExternalRotation", "HipFlexion"),
    "HipInternalRotation": ("HipExternalRotation", "HipFlexion"),
    "KneeExtension": ("KneeFlexion", "HipFlexion"),
    "KneeFlexion": ("KneeFlexion", "HipFlexion"),

}

# Define the range of motion for each study
range_of_motion = {
"AnkleDorsiFlexion": np.array([30, -30]),
"AnklePlantarFlexion": np.array([-30, 30]),
"KneeFlexion": np.array([0, 160]),
"KneeExtension": np.array([160, 0]),
"SubTalarEversion": np.array([-20.0, 20.0]),
"SubTalarInversion": np.array([-20.0, 20.0]),
"HipAbduction": np.array([-15, 40]),
"HipAdduction": np.array([40, -15]),
"HipExtension": np.array([130, -5]),
"HipFlexion": np.array([-5, 130]),
"HipExternalRotation": np.array([-20.0, 20.0]),
"HipInternalRotation": np.array([-20.0, 20.0]),
}

# Define the range of motion for each study
rom_secondary_dof = {
"AnklePlantarFlexion": np.array([-30, 30]),
"KneeFlexion": np.array([0, 160]),
"HipFlexion": np.array([-5, 130]),
}


MUSCLE_TYPES = ["Simple", "3E_1Par", "Strong3E_2Par", "3E_Experimental"]


def generate_muscle_calibration_macros() -> list[list[mc.MacroCommand]]:
    ## Save calibration files for all muscle models
    calibration_macros = []
    for muscle_type in MUSCLE_TYPES:
        calibration_macros.append([
            mc.Load("EvaluateJointStrength.main.any"),
            mc.OperationRun("Main.HumanModel.Calibration.CalibrationSequence"),
            mc.SaveValues(f"{muscle_type}_calibration.anyset")
        ])
    return calibration_macros




def generate_muscle_simulation_macros()-> list[list[mc.MacroCommand]]:
    macros = []

    for study, (primary_dof, secondary_dof) in simulation_plan.items():
        for muscle_type in MUSCLE_TYPES:
            rom_primary = range_of_motion[study]
            submacros = []
            rom_secondary = np.linspace(*rom_secondary_dof[secondary_dof], 40)
            for secondary_val in rom_secondary:
                submacros.append([
                    mc.Load("EvaluateJointStrength.main.any"),
                    # Load the calibration for the given muscle model
                    mc.LoadValues(f"{muscle_type}_calibration.anyset"),
                    mc.UpdateValues(),
                    # Set parameters for easier output
                    mc.SetValue(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.RangeOfMotion", rom_primary ),
                    mc.SetValue(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.{secondary_dof}", secondary_val),
                    # Run the inverse dynamics study
                    mc.OperationRun(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.Study.InverseDynamics"),
                    # Export results
                    mc.Export(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.Study.Output.JointStrength.Abscissa.JointAngle", "measurePrimaryDoF"),
                    mc.Export(f"Main.HumanModel.EvaluateJointStrength.Right.Leg.{study}.Study.Output.JointStrength.JointStrength", "measureValue"),
                    mc.Export("Main.AMMRGitBranch", "ammr_git_branch"),
                    mc.Export("Main.AMMRGitHash", "ammr_git_hash"),
                    mc.Export("Main.AnyBodyVersion", "anybody_version"),
                    mc.ExtendOutput("AnyBodyMuscleType", muscle_type),
                    mc.ExtendOutput("measureObject", study_map[study]),
                    mc.ExtendOutput("primaryDoF", dof_map[primary_dof][0]),
                    mc.ExtendOutput("secondaryDoF", dof_map[secondary_dof][0]),
                    mc.ExtendOutput("measureSecondDoF", secondary_val),
                    # Add sign conventions, so we can later correct the output to mactch strength dataset from the publication
                    mc.ExtendOutput("measureSecondDoFSign", dof_map[secondary_dof][1]),
                    mc.ExtendOutput("measurePrimaryDoFSign", dof_map[primary_dof][1]),
                ])
            macros.extend(submacros)
    return macros

@app.command()
def batch_process(batch: int|None = None, num_batches: int|None = None):
    """ Run the joint strength evaluation in batches.
    If batch and num_batches are provided, only the given batch is processed.
    """

    # app = AnyPyProcess()
    # cal_macros = generate_muscle_calibration_macros()
    # print("Running calibration macros...")
    # results = app.start_macro(cal_macros)
    # assert "ERROR" not in results, f"Failed with: {results['ERROR']}"

    macros = generate_muscle_simulation_macros()

    if num_batches and num_batches > len(macros):
        raise ValueError("number_of_batches is larger than the number of macros")

    if batch is not None and num_batches:
        batch_len = (len(macros) + num_batches - 1) // num_batches
        macros = list(list(itertools.batched(macros, batch_len))[batch-1])

    app = AnyPyProcess(num_processes=5)
    print("Running strength evaluation macros...")
    results = app.start_macro(macros)
    assert "ERROR" not in results, f"Failed with: {results['ERROR']}"

    df_pandas = results.to_dataframe(index_var="measurePrimaryDoF")

    # Change signs of variables which are opposite to the AnyBody convention
    df = pl.from_pandas(df_pandas).with_columns(
        pl.col("measureSecondDoF")*pl.col("measureSecondDoFSign").alias("measureSecondDoF"),
        pl.col("measurePrimaryDoF")*pl.col("measurePrimaryDoFSign").alias("measurePrimaryDoF"),
    ).drop(["measureSecondDoFSign", "measurePrimaryDoFSign"])

    batch_label = f"{batch}" if batch else ""
    df.write_parquet(f"joint_strength_results_{batch_label}.parquet")

number_of_batches = 100

@app.command()
def cleanup_parquet_files():
    for fn in glob.glob("joint_strength_*.parquet"):
        os.remove(fn)


@app.command()
def combine_parquet_files(input_pattern: str = "joint_strength_*.parquet", output: str = "joint_strength.parquet"):
    # concatenate all parquet files file
    pl.scan_parquet(input_pattern).sink_parquet(output)


if __name__ == "__main__":
    app()

