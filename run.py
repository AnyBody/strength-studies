
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

# Define the second  range of motion for each study
secondary_dof_rom_values = {
"AnklePlantarFlexion": np.array([-20, 0, 20]),
"KneeFlexion": np.array([0, 70, 160]),
"HipFlexion": np.array([-5, 0, 60, 130]),
}


MUSCLE_TYPES = ["Simple", "3E_1Par", "Strong3E_2Par", "3E_Experimental"]


def run_calibration():
    """ Run calibration for all muscle models and save the calibration files."""

    calibration_macros = [
        [
            mc.Load("EvaluateJointStrength.main.any", defs={"MUSCLE_TYPE": f'"{muscle_type}"'}),
            mc.OperationRun("Main.HumanModel.Calibration.CalibrationSequence"),
            mc.SaveValues(f"{muscle_type}_calibration.anyset")
        ]
        for muscle_type in MUSCLE_TYPES
    ]
    app = AnyPyProcess()
    print("Running calibration macros...")
    results = app.start_macro(calibration_macros)
    for res in results:
        assert "ERROR" not in res, f"Failed with: {res['ERROR']}"


def generate_muscle_simulation_macros()-> list[list[mc.MacroCommand]]:
    macros = []

    for study, (primary_dof, secondary_dof) in simulation_plan.items():
        for muscle_type in MUSCLE_TYPES:
            rom_primary = range_of_motion[study]
            submacros = []
            for secondary_val in secondary_dof_rom_values[secondary_dof]:
                submacros.append([
                    mc.Load("EvaluateJointStrength.main.any", defs={"MUSCLE_TYPE": f'"{muscle_type}"'}),
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


def distribute_batches(items: list, batch: int, num_batches: int) -> list:
    """Distribute items across batches, returning items for the specified batch.
    
    Args:
        items: List of items to distribute
        batch: The batch number (1-indexed)
        num_batches: Total number of batches
        
    Returns:
        Subset of items for the specified batch
    """
    total_items = len(items)
    batch_size = total_items // num_batches
    remainder = total_items % num_batches
    
    # Calculate start and end indices for this batch
    # Give extra items to first 'remainder' batches
    if batch <= remainder:
        start_idx = (batch - 1) * (batch_size + 1)
        end_idx = start_idx + batch_size + 1
    else:
        start_idx = remainder * (batch_size + 1) + (batch - remainder - 1) * batch_size
        end_idx = start_idx + batch_size
    
    return items[start_idx:end_idx]





@app.command()
def batch_process(batch: int|None = None, num_batches: int|None = None):
    """ Run the joint strength evaluation in batches.
    If batch and num_batches are provided, only the given batch is processed.
    """

    run_calibration()

    macros = generate_muscle_simulation_macros()

    if num_batches and num_batches > len(macros):
        raise ValueError("number_of_batches is larger than the number of macros")
    if batch is not None and num_batches:
        macros = distribute_batches(macros, batch, num_batches)

    app = AnyPyProcess(num_processes=5)
    print("Running strength evaluation macros...")
    results = app.start_macro(macros)

    for res in results:
        assert "ERROR" not in res, f"Failed with: {res['ERROR']}"

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
    pl.read_parquet(input_pattern).write_parquet(output)


if __name__ == "__main__":
    app()

